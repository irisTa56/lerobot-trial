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
    use std::{
        path::PathBuf,
        sync::{Arc, RwLock},
    };

    const ACTION_OUTPUT_ID: &str = "action";
    const RESET_OUTPUT_ID: &str = "reset";

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from lerobot-trial!".to_string()
    }

    /// Create DoraHandler and RerunClient together, sharing the same log channel
    #[pyfunction]
    #[pyo3(signature = (grpc_url=None, rrd_path=None, flush_tick_millis=None))]
    fn create_handlers(
        grpc_url: Option<String>,
        rrd_path: Option<PathBuf>,
        flush_tick_millis: Option<u64>,
    ) -> PyResult<(PyDoraHandler, PyRerunClient)> {
        let (rerun, log_tx) =
            RerunClient::init(grpc_url, rrd_path, flush_tick_millis).map_err(|e| {
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
        #[pyo3(signature = (path, data, width, height, quality=75))]
        fn log_rgb_image(
            &self,
            path: String,
            data: Vec<u8>,
            width: u32,
            height: u32,
            quality: u8,
        ) -> PyResult<()> {
            self.inner
                .read()
                .unwrap()
                .send_log_request(LogRequest::LogRgbImage {
                    path,
                    data,
                    width,
                    height,
                    quality,
                })
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to log RGB image: {}", e)))
        }

        fn start_recording(&self) -> PyResult<()> {
            self.inner
                .read()
                .unwrap()
                .send_log_request(LogRequest::StartRecording)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to start recording: {}", e)))
        }

        fn stop_recording(&self) -> PyResult<()> {
            self.inner
                .read()
                .unwrap()
                .send_log_request(LogRequest::StopRecording)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to stop recording: {}", e)))
        }

        fn shutdown(&self) -> PyResult<()> {
            self.inner
                .read()
                .unwrap()
                .send_log_request(LogRequest::Shutdown)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to shutdown: {}", e)))
        }

        fn is_running(&self) -> bool {
            self.inner.read().unwrap().is_running()
        }
    }
}
