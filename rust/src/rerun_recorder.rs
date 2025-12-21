use rerun::{
    EncodedImage, Image, RecordingStreamBuilder, Scalars,
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
    Image {
        path: String,
        data: Vec<u8>,
        width: u32,
        height: u32,
    },
    EncodedImage {
        path: String,
        data: Vec<u8>,
    },
    Scalars {
        path: String,
        values: Vec<f64>,
    },
}

#[derive(Debug)]
pub(crate) struct RerunRecorder {
    log_tx: Sender<LogRequest>,
    log_handle: JoinHandle<()>,
}

impl RerunRecorder {
    const APP_NAME: &str = "lerobot_trial";

    pub(crate) fn init(
        rrd_path: Option<impl Into<PathBuf>>,
    ) -> Result<(Self, Sender<LogRequest>), BoxedError> {
        let builder = RecordingStreamBuilder::new(Self::APP_NAME)
            .batcher_config(ChunkBatcherConfig::LOW_LATENCY);

        let rec = if let Some(path) = rrd_path {
            builder.set_sinks((GrpcSink::default(), FileSink::new(path)?))?
        } else {
            builder.connect_grpc()?
        };

        let (log_tx, log_rx) = mpsc::channel::<LogRequest>();

        let log_handle = thread::spawn(move || {
            while let Ok(request) = log_rx.recv() {
                let result = match request {
                    LogRequest::Image {
                        path,
                        data,
                        width,
                        height,
                    } => rec.log(path.as_str(), &Image::from_rgb24(data, [width, height])),
                    LogRequest::EncodedImage { path, data } => {
                        rec.log(path.as_str(), &EncodedImage::from_file_contents(data))
                    }
                    LogRequest::Scalars { path, values } => {
                        rec.log(path.as_str(), &Scalars::new(values))
                    }
                };

                if let Err(e) = result {
                    eprintln!("Failed to log to Rerun: {}", e);
                }
            }
        });

        let recorder = Self {
            log_tx: log_tx.clone(),
            log_handle,
        };

        Ok((recorder, log_tx))
    }

    pub(crate) fn send_log_request(&self, request: LogRequest) -> Result<(), BoxedError> {
        self.log_tx
            .send(request)
            .map_err(|e| format!("Failed to send log request: {}", e).into())
    }

    pub(crate) fn is_running(&self) -> bool {
        !self.log_handle.is_finished()
    }
}
