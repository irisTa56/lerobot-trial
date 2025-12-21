use crate::rerun_recorder::LogRequest;
use dora_message::id::DataId;
use dora_node_api::{
    DoraNode, Event, Metadata, MetadataParameters, Parameter,
    arrow::{
        array::{ArrayRef, AsArray},
        datatypes::{DataType, Float64Type},
    },
};
use std::{
    collections::BTreeMap,
    sync::{
        Arc, Mutex,
        mpsc::{self, Receiver, SendError, Sender},
    },
    thread::{self, JoinHandle},
};

type BoxedError = Box<dyn std::error::Error>;
type DataReceiver = Receiver<(DataId, ArrayRef, Vec<usize>)>;
type SendRequest = (String, ArrayRef, MetadataParameters);

#[derive(Debug)]
pub(crate) struct DoraHandler {
    send_tx: Sender<SendRequest>,
    recv_rx: Arc<Mutex<DataReceiver>>,
    recv_handle: JoinHandle<()>,
}

impl DoraHandler {
    pub(crate) fn new(log_tx: Sender<LogRequest>) -> Result<Self, BoxedError> {
        let (mut node, mut events) = DoraNode::init_from_env()?;

        let (recv_tx, recv_rx) = mpsc::channel();
        let (send_tx, send_rx) = mpsc::channel::<SendRequest>();

        let recv_handle = thread::spawn(move || {
            while let Some(event) = events.recv() {
                match event {
                    Event::Input { id, data, metadata } => {
                        let shape = extract_shape_from_metadata(&metadata)
                            .unwrap_or_else(|| vec![data.len()]);
                        let array = ArrayRef::from(data);

                        match (shape.len(), array.data_type()) {
                            (1, DataType::Float64) => {
                                let request = LogRequest::LogScalars {
                                    path: id.clone().into(),
                                    values: array.as_primitive::<Float64Type>().values().to_vec(),
                                };
                                if let Err(e) = log_tx.send(request) {
                                    eprintln!("Failed to send log request: {:?}", e);
                                }
                            }
                            (_, data_type) => eprintln!(
                                "Unsupported data type for logging: {:?} with shape {:?}",
                                data_type, shape
                            ),
                        }

                        if let Err(e) = recv_tx.send((id, array, shape)) {
                            eprintln!("Failed to send received data: {:?}", e);
                        }
                    }
                    Event::Stop(_) => println!("Received stop signal from Dora."),
                    _ => eprintln!("Unexpected event: {:?}", event),
                }
            }
        });

        thread::spawn(move || {
            while let Ok((output_id, data, parameters)) = send_rx.recv() {
                if let Err(e) = node.send_output(output_id.clone().into(), parameters, data) {
                    eprintln!("Failed to send output '{}': {:?}", output_id, e);
                }
            }
        });

        Ok(Self {
            send_tx,
            recv_rx: Arc::new(Mutex::new(recv_rx)),
            recv_handle,
        })
    }

    pub(crate) fn try_recv(&self) -> Option<(String, ArrayRef, Vec<usize>)> {
        let (id, array, shape) = self.recv_rx.lock().unwrap().try_recv().ok()?;
        Some((id.into(), array, shape))
    }

    pub(crate) fn is_running(&self) -> bool {
        !self.recv_handle.is_finished()
    }

    pub(crate) fn send_output(
        &self,
        output_id: String,
        data: ArrayRef,
        parameters: BTreeMap<String, Parameter>,
    ) -> Result<(), SendError<SendRequest>> {
        self.send_tx.send((output_id, data, parameters))
    }
}

/// Extract shape information from metadata parameters.
/// Returns Some(Vec<usize>) if shape is found and valid, None otherwise.
fn extract_shape_from_metadata(metadata: &Metadata) -> Option<Vec<usize>> {
    metadata
        .parameters
        .get("shape")
        .and_then(|param| match param {
            Parameter::ListInt(v) => v.iter().map(|i| usize::try_from(*i).ok()).collect(),
            _ => None,
        })
}
