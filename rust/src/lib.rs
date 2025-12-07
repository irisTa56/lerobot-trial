mod dora_threads;

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pyo3::pymodule]
mod _rust {
    use crate::dora_threads::DoraThreadsHandle;
    use pyo3::{exceptions::PyRuntimeError, prelude::*};
    use pyo3_arrow::{PyArray, error::PyArrowResult};

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from lerobot-trial!".to_string()
    }

    #[pyclass]
    struct DoraNode {
        inner: DoraThreadsHandle,
    }

    #[pyclass]
    struct DoraInput {
        #[pyo3(get)]
        id: String,
        #[pyo3(get)]
        array: PyObject,
    }

    #[pymethods]
    impl DoraNode {
        #[new]
        fn new() -> PyResult<Self> {
            let inner = DoraThreadsHandle::new().map_err(|e| {
                PyRuntimeError::new_err(format!("Failed to initialize DoraNode: {}", e))
            })?;
            Ok(Self { inner })
        }

        fn try_recv(&self, py: Python) -> PyArrowResult<Option<DoraInput>> {
            let Some((id, data)) = self.inner.try_recv() else {
                return Ok(None);
            };

            let array = PyArray::from_array_ref(data).to_pyarrow(py)?.into();
            Ok(Some(DoraInput { id, array }))
        }

        fn is_running(&self) -> bool {
            self.inner.is_running()
        }
    }
}
