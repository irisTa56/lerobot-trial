use image::{ExtendedColorType, ImageBuffer, Rgb, codecs::jpeg::JpegEncoder};
use rerun::{
    DEFAULT_CONNECT_URL, EncodedImage, RecordingStream, RecordingStreamBuilder, Scalars,
    external::re_uri::ProxyUri,
    log::ChunkBatcherConfig,
    sink::{FileSink, GrpcSink, LogSink},
};
use std::{
    io::Cursor,
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
    LogRgbImage {
        path: String,
        data: Vec<u8>,
        width: u32,
        height: u32,
        quality: u8,
    },
    LogScalars {
        path: String,
        values: Vec<f64>,
    },
    StartRecording,
    StopRecording,
    Shutdown,
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
        let mut handler = StreamHandler::try_new(grpc_url, rrd_path, flush_tick)?;

        let (log_tx, log_rx) = mpsc::channel();

        let log_handle = thread::spawn(move || {
            while let Ok(request) = log_rx.recv() {
                match handler.process_request(request) {
                    Ok(true) => continue,
                    Ok(false) => break,
                    Err(e) => eprintln!("Failed to process request: {:?}", e),
                }
            }
        });

        let client = Self {
            log_tx: log_tx.clone(),
            log_handle,
        };

        Ok((client, log_tx))
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
    stream: RecordingStream,
    grpc_url: String,
    rrd_path: Option<PathBuf>,
    flush_tick: Duration,
    recording: bool,
}

impl StreamHandler {
    fn try_new(
        grpc_url: String,
        rrd_path: Option<PathBuf>,
        flush_tick: Duration,
    ) -> Result<Self, BoxedError> {
        let stream = build_recording_stream(&grpc_url, None, flush_tick)?;

        Ok(Self {
            stream,
            grpc_url,
            rrd_path,
            flush_tick,
            recording: false,
        })
    }

    fn process_request(&mut self, request: LogRequest) -> Result<bool, BoxedError> {
        match request {
            LogRequest::LogRgbImage {
                path,
                data,
                width,
                height,
                quality,
            } => {
                let jpeg_data = encode_rgb_to_jpeg(&data, width, height, quality)?;
                let image = EncodedImage::from_file_contents(jpeg_data);
                if self.recording {
                    self.stream.log(path, &image)?;
                } else {
                    // Log as static data to reduce memory usage in the viewer
                    self.stream.log_static(path, &image)?;
                }
            }
            LogRequest::LogScalars { path, values } => {
                let scalars = Scalars::new(values);
                self.stream.log(path, &scalars)?;
            }
            LogRequest::StartRecording => self.reset_stream(true)?,
            LogRequest::StopRecording => self.reset_stream(false)?,
            LogRequest::Shutdown => {
                self.stream.flush_blocking()?;
                return Ok(false);
            }
        }

        Ok(true)
    }

    fn reset_stream(&mut self, recording: bool) -> Result<(), BoxedError> {
        if recording == self.recording {
            return Err(format!("Recording state is already {}", recording).into());
        }

        self.stream.flush_blocking()?;
        self.stream = build_recording_stream(
            &self.grpc_url,
            self.rrd_path.as_ref().filter(|_| recording),
            self.flush_tick,
        )?;
        self.recording = recording;
        Ok(())
    }
}

fn build_recording_stream(
    grpc_url: &str,
    rrd_path: Option<&PathBuf>,
    flush_tick: Duration,
) -> Result<RecordingStream, BoxedError> {
    let grpc_uri = ProxyUri::from_str(grpc_url)?;
    let mut sinks: Vec<Box<dyn LogSink>> = vec![Box::new(GrpcSink::new(grpc_uri))];

    if let Some(path) = rrd_path {
        sinks.push(Box::new(FileSink::new(path)?));
    }

    let config = ChunkBatcherConfig {
        flush_tick,
        ..Default::default()
    };
    let builder = RecordingStreamBuilder::new(APP_NAME).batcher_config(config);
    Ok(builder.set_sinks(sinks)?)
}

fn encode_rgb_to_jpeg(
    rgb_data: &[u8],
    width: u32,
    height: u32,
    quality: u8,
) -> Result<Vec<u8>, BoxedError> {
    let img: ImageBuffer<Rgb<u8>, _> =
        ImageBuffer::from_raw(width, height, rgb_data).ok_or("Invalid image dimensions")?;

    let mut jpeg_data = Cursor::new(Vec::new());
    let mut encoder = JpegEncoder::new_with_quality(&mut jpeg_data, quality);
    encoder.encode(img.as_raw(), width, height, ExtendedColorType::Rgb8)?;

    Ok(jpeg_data.into_inner())
}
