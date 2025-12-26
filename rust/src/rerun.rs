use rerun::{
    DEFAULT_CONNECT_URL, EncodedImage, RecordingStream, RecordingStreamBuilder, Scalars,
    external::re_uri::ProxyUri,
    log::ChunkBatcherConfig,
    sink::{FileSink, GrpcSink, LogSink},
};
use std::{
    path::PathBuf,
    str::FromStr,
    sync::mpsc::{self, Sender},
    thread::{self, JoinHandle},
    time::Duration,
};

type BoxedError = Box<dyn std::error::Error>;

const APP_NAME: &str = "lerobot_trial";
const DEFAULT_FLUSH_TICK_MILLIS: u64 = 100;

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
    log_handle: JoinHandle<()>,
}

impl RerunClient {
    pub(crate) fn init(
        grpc_url: Option<String>,
        rrd_path: Option<PathBuf>,
        flush_tick_millis: Option<u64>,
    ) -> Result<(Self, Sender<LogRequest>), BoxedError> {
        let grpc_url = grpc_url.unwrap_or_else(|| DEFAULT_CONNECT_URL.into());
        let flush_tick_millis = flush_tick_millis.unwrap_or(DEFAULT_FLUSH_TICK_MILLIS);
        let flush_tick = Duration::from_millis(flush_tick_millis);
        let mut handler = StreamHandler::new(grpc_url, rrd_path, flush_tick);

        let (log_tx, log_rx) = mpsc::channel();

        let log_handle = thread::spawn(move || {
            while let Ok(request) = log_rx.recv() {
                if let Err(e) = handler.process_request(request) {
                    eprintln!("Failed to process request: {}", e);
                }
            }
        });

        let client = Self {
            log_tx: log_tx.clone(),
            log_handle,
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
        !self.log_handle.is_finished()
    }
}

#[derive(Debug)]
struct StreamHandler {
    stream: Option<RecordingStream>,
    grpc_url: String,
    rrd_path: Option<PathBuf>,
    flush_tick: Duration,
}

impl StreamHandler {
    fn new(grpc_url: String, rrd_path: Option<PathBuf>, flush_tick: Duration) -> Self {
        Self {
            stream: None,
            grpc_url,
            rrd_path,
            flush_tick,
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
        let grpc_uri = ProxyUri::from_str(&self.grpc_url)?;
        let mut sinks: Vec<Box<dyn LogSink>> = vec![Box::new(GrpcSink::new(grpc_uri))];

        if let Some(path) = &self.rrd_path {
            sinks.push(Box::new(FileSink::new(path)?));
        }

        let config = ChunkBatcherConfig {
            flush_tick: self.flush_tick,
            ..Default::default()
        };
        let builder = RecordingStreamBuilder::new(APP_NAME).batcher_config(config);

        let stream = builder.set_sinks(sinks)?;

        self.stream = Some(stream);
        Ok(())
    }
}
