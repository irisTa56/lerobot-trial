mod dora;
mod rerun;

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pyo3::pymodule]
mod _rust {
    use crate::{
        dora::DoraHandler,
        rerun::{LogRequest, RerunClient},
    };
    use dora_node_api::arrow::array::{BooleanArray, Float64Array};
    use pyo3::{exceptions::PyRuntimeError, prelude::*};
    use pyo3_arrow::{PyArray, error::PyArrowResult};
    use std::sync::{Arc, RwLock};

    const ACTION_OUTPUT_ID: &str = "action";
    const RESET_OUTPUT_ID: &str = "reset";

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from lerobot-trial!".to_string()
    }

    /// Create DoraHandler and RerunClient together, sharing the same log channel
    #[pyfunction]
    fn create_handlers() -> PyResult<(PyDoraHandler, PyRerunClient)> {
        let (rerun, log_tx) = RerunClient::init().map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to initialize RerunClient: {}", e))
        })?;

        let dora = DoraHandler::new(log_tx).map_err(|e| {
            PyRuntimeError::new_err(format!("Failed to initialize DoraHandler: {}", e))
        })?;

        Ok((
            PyDoraHandler { inner: dora },
            PyRerunClient {
                inner: RwLock::new(rerun),
            },
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
            let data = Arc::new(Float64Array::from(data));
            self.inner
                .send_output(ACTION_OUTPUT_ID.to_string(), data, Default::default())
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to send action: {}", e)))
        }

        fn send_reset(&self) -> PyResult<()> {
            let data = Arc::new(BooleanArray::from(vec![true]));
            self.inner
                .send_output(RESET_OUTPUT_ID.to_string(), data, Default::default())
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to send reset: {}", e)))
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

    #[pyclass(name = "RerunClient")]
    struct PyRerunClient {
        // RwLock is needed because start/stop_recording() require &mut self
        inner: RwLock<RerunClient>,
    }

    #[pymethods]
    impl PyRerunClient {
        fn log_encoded_image(&self, path: String, data: Vec<u8>) -> PyResult<()> {
            self.inner
                .read()
                .unwrap()
                .send_log_request(LogRequest::LogEncodedImage { path, data })
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to log encoded image: {}", e)))
        }

        #[pyo3(signature = (rrd_path=None))]
        fn start_recording(&self, rrd_path: Option<String>) -> PyResult<()> {
            self.inner
                .write()
                .unwrap()
                .start_recording(rrd_path)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to start recording: {}", e)))
        }

        fn stop_recording(&self) -> PyResult<()> {
            self.inner
                .write()
                .unwrap()
                .stop_recording()
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to stop recording: {}", e)))
        }

        fn is_running(&self) -> bool {
            self.inner.read().unwrap().is_running()
        }
    }
}
