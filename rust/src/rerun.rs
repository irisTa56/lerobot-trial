use rerun::{
    EncodedImage, RecordingStream, RecordingStreamBuilder, Scalars,
    log::ChunkBatcherConfig,
    sink::{FileSink, GrpcSink},
};
use std::{
    path::PathBuf,
    sync::mpsc::{self, Sender},
    thread::{self, JoinHandle},
};

type BoxedError = Box<dyn std::error::Error>;

#[derive(Debug)]
pub(crate) enum LogRequest {
    LogEncodedImage { path: String, data: Vec<u8> },
    LogScalars { path: String, values: Vec<f64> },
    StartRecording,
    StopRecording,
}

#[derive(Debug)]
pub(crate) struct RerunClient {
    log_tx: Sender<LogRequest>,
    log_handle: Option<JoinHandle<()>>,
}

impl RerunClient {
    const APP_NAME: &str = "lerobot_trial";

    pub(crate) fn init(
        rrd_path: Option<impl Into<PathBuf>>,
    ) -> Result<(Self, Sender<LogRequest>), BoxedError> {
        let (log_tx, log_rx) = mpsc::channel();
        let mut handler = StreamHandler::new(rrd_path);

        let log_handle = thread::spawn(move || {
            while let Ok(request) = log_rx.recv() {
                if let Err(e) = handler.process_request(request) {
                    eprintln!("Failed to process request: {}", e);
                }
            }
        });

        let client = Self {
            log_tx: log_tx.clone(),
            log_handle: Some(log_handle),
        };

        Ok((client, log_tx))
    }

    pub(crate) fn start_recording(&mut self) -> Result<(), BoxedError> {
        self.send_log_request(LogRequest::StartRecording)
    }

    pub(crate) fn stop_recording(&mut self) -> Result<(), BoxedError> {
        self.send_log_request(LogRequest::StopRecording)
    }

    pub(crate) fn send_log_request(&self, request: LogRequest) -> Result<(), BoxedError> {
        self.log_tx.send(request)?;
        Ok(())
    }

    pub(crate) fn is_running(&self) -> bool {
        self.log_handle.as_ref().is_some_and(|h| !h.is_finished())
    }
}

#[derive(Debug)]
struct StreamHandler {
    stream: Option<RecordingStream>,
    rrd_path: Option<PathBuf>,
}

impl StreamHandler {
    fn new(rrd_path: Option<impl Into<PathBuf>>) -> Self {
        Self {
            stream: None,
            rrd_path: rrd_path.map(Into::into),
        }
    }

    fn process_request(&mut self, request: LogRequest) -> Result<(), BoxedError> {
        match (&self.stream, request) {
            (None, LogRequest::StartRecording) => {
                self.start_recording()?;
            }
            (Some(stream), LogRequest::StopRecording) => {
                stream.flush_blocking()?;
                self.stream = None;
            }
            (Some(stream), LogRequest::LogEncodedImage { path, data }) => {
                stream.log(path, &EncodedImage::from_file_contents(data))?;
            }
            (Some(stream), LogRequest::LogScalars { path, values }) => {
                stream.log(path, &Scalars::new(values))?;
            }
            (Some(_), LogRequest::StartRecording) => {
                return Err("Recording is already running".into());
            }
            (None, LogRequest::StopRecording) => {
                return Err("Recording is not running".into());
            }
            _ => (),
        }

        Ok(())
    }

    fn start_recording(&mut self) -> Result<(), BoxedError> {
        let builder = RecordingStreamBuilder::new(RerunClient::APP_NAME)
            .batcher_config(ChunkBatcherConfig::LOW_LATENCY);

        let stream = match &self.rrd_path {
            Some(path) => builder.set_sinks((GrpcSink::default(), FileSink::new(path)?))?,
            None => builder.connect_grpc()?,
        };

        self.stream = Some(stream);
        Ok(())
    }
}
