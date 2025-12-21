use rerun::{
    AsComponents, EncodedImage, Image, RecordingStream, RecordingStreamBuilder, Scalars,
    log::ChunkBatcherConfig,
    sink::{FileSink, GrpcSink},
};
use std::{
    path::PathBuf,
    sync::{
        Arc, Mutex,
        mpsc::{self, Receiver, Sender},
    },
    thread::{self, JoinHandle},
    time::Instant,
};

type BoxedError = Box<dyn std::error::Error>;

#[derive(Debug)]
pub(crate) enum LogRequest {
    LogImage {
        path: String,
        data: Vec<u8>,
        width: u32,
        height: u32,
    },
    LogEncodedImage {
        path: String,
        data: Vec<u8>,
    },
    LogScalars {
        path: String,
        values: Vec<f64>,
    },
    StartRecording,
    StopRecording,
}

#[derive(Debug)]
pub(crate) struct RerunRecorder {
    log_tx: Sender<LogRequest>,
    log_handle: Arc<Mutex<Option<JoinHandle<()>>>>,
}

impl RerunRecorder {
    const APP_NAME: &str = "lerobot_trial";

    pub(crate) fn init(
        rrd_path: Option<impl Into<PathBuf>>,
    ) -> Result<(Self, Sender<LogRequest>), BoxedError> {
        let rrd_path = rrd_path.map(|p| p.into());
        let (log_tx, log_rx) = mpsc::channel();

        let log_handle = Self::spawn_log_thread(log_rx, rrd_path)?;

        let recorder = Self {
            log_tx: log_tx.clone(),
            log_handle: Arc::new(Mutex::new(Some(log_handle))),
        };

        Ok((recorder, log_tx))
    }

    fn spawn_log_thread(
        log_rx: Receiver<LogRequest>,
        rrd_path: Option<PathBuf>,
    ) -> Result<JoinHandle<()>, BoxedError> {
        Ok(thread::spawn(move || {
            let mut session = RecordingSession::new(rrd_path);

            while let Ok(request) = log_rx.recv() {
                session.process_request(request);
            }
        }))
    }

    pub(crate) fn start_recording(&mut self) -> Result<(), BoxedError> {
        self.log_tx
            .send(LogRequest::StartRecording)
            .map_err(|e| format!("Failed to send start recording request: {}", e).into())
    }

    pub(crate) fn stop_recording(&mut self) -> Result<(), BoxedError> {
        self.log_tx
            .send(LogRequest::StopRecording)
            .map_err(|e| format!("Failed to send stop recording request: {}", e).into())
    }

    pub(crate) fn send_log_request(&self, request: LogRequest) -> Result<(), BoxedError> {
        self.log_tx
            .send(request)
            .map_err(|e| format!("Failed to send log request: {}", e).into())
    }

    pub(crate) fn is_running(&self) -> bool {
        self.log_handle
            .lock()
            .unwrap()
            .as_ref()
            .is_some_and(|h| !h.is_finished())
    }
}

struct RecordingSession {
    stream: Option<RecordingStream>,
    rrd_path: Option<PathBuf>,
}

impl RecordingSession {
    fn new(rrd_path: Option<PathBuf>) -> Self {
        Self {
            stream: None,
            rrd_path,
        }
    }

    fn process_request(&mut self, request: LogRequest) {
        match request {
            LogRequest::StartRecording => {
                if let Err(e) = self.start_recording() {
                    eprintln!("Failed to start recording: {}", e);
                }
            }
            LogRequest::StopRecording => {
                if let Some(ref mut stream) = self.stream {
                    let start = Instant::now();
                    if let Err(e) = stream.flush_blocking() {
                        eprintln!("Failed to flush Rerun stream: {}", e);
                    }
                    println!("Flushed Rerun stream in {:.2?}", start.elapsed());
                }
                self.stream = None
            }
            _ if self.stream.is_none() => {}
            LogRequest::LogImage {
                path,
                data,
                width,
                height,
            } => self.log_data(path.as_str(), &Image::from_rgb24(data, [width, height])),
            LogRequest::LogEncodedImage { path, data } => {
                self.log_data(path.as_str(), &EncodedImage::from_file_contents(data))
            }
            LogRequest::LogScalars { path, values } => {
                self.log_data(path.as_str(), &Scalars::new(values))
            }
        }
    }

    fn start_recording(&mut self) -> Result<(), BoxedError> {
        let builder = RecordingStreamBuilder::new(RerunRecorder::APP_NAME)
            .batcher_config(ChunkBatcherConfig::LOW_LATENCY);

        let stream = match &self.rrd_path {
            Some(path) => builder.set_sinks((GrpcSink::default(), FileSink::new(path)?))?,
            None => builder.connect_grpc()?,
        };

        self.stream = Some(stream);
        Ok(())
    }

    fn log_data<T: AsComponents>(&self, path: &str, data: &T) {
        if let Some(ref stream) = self.stream
            && let Err(e) = stream.log(path, data)
        {
            eprintln!("Failed to log to Rerun: {}", e);
        }
    }
}
