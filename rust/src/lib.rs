mod dora_handler;
mod rerun_recorder;

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pyo3::pymodule]
mod _rust {
    use crate::{dora_handler::DoraHandler, rerun_recorder::RerunRecorder};
    use pyo3::{exceptions::PyRuntimeError, prelude::*};
    use pyo3_arrow::{PyArray, error::PyArrowResult};

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from lerobot-trial!".to_string()
    }

    #[pyclass(name = "DoraHandler")]
    struct PyDoraHandler {
        inner: DoraHandler,
    }

    #[pymethods]
    impl PyDoraHandler {
        #[new]
        fn new() -> PyResult<Self> {
            let inner = DoraHandler::new().map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to initialize DoraHandler: {}", e))
            })?;
            Ok(Self { inner })
        }

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
    }

    #[pyclass(name = "RerunRecorder")]
    struct PyRerunRecorder {
        inner: RerunRecorder,
    }

    #[pymethods]
    impl PyRerunRecorder {
        #[new]
        #[pyo3(signature = (rrd_path=None))]
        fn new(rrd_path: Option<String>) -> PyResult<Self> {
            let inner = RerunRecorder::new(rrd_path).map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to initialize RerunRecorder: {}", e))
            })?;
            Ok(Self { inner })
        }

        fn log_rgb_image(
            &self,
            path: String,
            data: Vec<u8>,
            width: u32,
            height: u32,
        ) -> PyResult<()> {
            self.inner
                .log_image(&path, data, width, height)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to log RGB image: {}", e)))
        }

        fn log_scalars(&self, path: String, values: Vec<f64>) -> PyResult<()> {
            self.inner
                .log_scalars(&path, values)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to log scalars: {}", e)))
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
