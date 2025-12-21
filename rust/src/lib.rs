mod dora_handler;
mod rerun_recorder;

const ACTION_OUTPUT_ID: &str = "action";

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pyo3::pymodule]
mod _rust {
    use crate::{
        ACTION_OUTPUT_ID,
        dora_handler::DoraHandler,
        rerun_recorder::{LogRequest, RerunRecorder},
    };
    use dora_node_api::arrow::array::Float64Array;
    use pyo3::{exceptions::PyRuntimeError, prelude::*};
    use pyo3_arrow::{PyArray, error::PyArrowResult};
    use std::sync::Arc;

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from lerobot-trial!".to_string()
    }

    /// Create DoraHandler and RerunRecorder together, sharing the same log channel
    #[pyfunction]
    #[pyo3(signature = (rrd_path=None))]
    fn create_handlers(rrd_path: Option<String>) -> PyResult<(PyDoraHandler, PyRerunRecorder)> {
        let (rerun, log_tx) = RerunRecorder::init(rrd_path).map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to initialize RerunRecorder: {}", e))
        })?;

        let dora = DoraHandler::new(log_tx).map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to initialize DoraHandler: {}", e))
        })?;

        Ok((
            PyDoraHandler { inner: dora },
            PyRerunRecorder { inner: rerun },
        ))
    }

    #[pyclass(name = "DoraHandler")]
    struct PyDoraHandler {
        inner: DoraHandler,
    }

    #[pymethods]
    impl PyDoraHandler {
        fn try_recv(&self, py: Python) -> PyArrowResult<Option<DoraInput>> {
            let Some((id, data, shape)) = self.inner.try_recv() else {
                return Ok(None);
            };

            let array = PyArray::from_array_ref(data).to_pyarrow(py)?.into();
            Ok(Some(DoraInput { id, array, shape }))
        }

        fn is_running(&self) -> bool {
            self.inner.is_running()
        }

        fn send_action(&self, data: Vec<f64>) -> PyResult<()> {
            let array = Arc::new(Float64Array::from(data));
            self.inner
                .send_output(ACTION_OUTPUT_ID.to_string(), array, Default::default())
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to send action: {}", e)))
        }
    }

    #[pyclass(name = "RerunRecorder")]
    struct PyRerunRecorder {
        inner: RerunRecorder,
    }

    #[pymethods]
    impl PyRerunRecorder {
        fn log_image(&self, path: String, data: Vec<u8>, width: u32, height: u32) -> PyResult<()> {
            self.inner
                .send_log_request(LogRequest::Image {
                    path,
                    data,
                    width,
                    height,
                })
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to log image: {}", e)))
        }

        fn is_running(&self) -> bool {
            self.inner.is_running()
        }
    }

    #[pyclass]
    pub(crate) struct DoraInput {
        #[pyo3(get)]
        id: String,
        #[pyo3(get)]
        array: PyObject,
        #[pyo3(get)]
        shape: Vec<usize>,
    }
}
