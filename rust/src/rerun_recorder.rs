use rerun::{
    Image, RecordingStream, RecordingStreamBuilder, Scalars,
    datatypes::{ChannelDatatype, ColorModel, ImageFormat},
    log::ChunkBatcherConfig,
    sink::{FileSink, GrpcSink},
};
use std::path::PathBuf;
type BoxedError = Box<dyn std::error::Error>;

#[derive(Debug)]
pub(crate) struct RerunRecorder {
    rec: RecordingStream,
}

impl RerunRecorder {
    const APP_NAME: &str = "lerobot_trial";

    pub(crate) fn new(rrd_path: Option<impl Into<PathBuf>>) -> Result<Self, BoxedError> {
        let builder = RecordingStreamBuilder::new(Self::APP_NAME)
            .batcher_config(ChunkBatcherConfig::LOW_LATENCY);

        let rec = if let Some(path) = rrd_path {
            builder.set_sinks((GrpcSink::default(), FileSink::new(path)?))?
        } else {
            builder.connect_grpc()?
        };

        Ok(Self { rec })
    }

    pub(crate) fn log_image(
        &self,
        path: &str,
        data: Vec<u8>,
        width: u32,
        height: u32,
    ) -> Result<(), BoxedError> {
        let format = ImageFormat {
            width,
            height,
            pixel_format: None, // RGB doesn't use PixelFormat
            color_model: Some(ColorModel::RGB),
            channel_datatype: Some(ChannelDatatype::U8),
        };

        self.rec.log(path, &Image::new(data, format))?;
        Ok(())
    }

    pub(crate) fn log_scalars(&self, path: &str, values: Vec<f64>) -> Result<(), BoxedError> {
        self.rec.log(path, &Scalars::new(values))?;
        Ok(())
    }
}
