use crate::rerun::LogRequest;
use dora_message::id::DataId;
use dora_node_api::{
    DoraNode, Event, MetadataParameters, Parameter,
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

#[derive(Debug)]
pub(crate) struct SendRequest {
    output_id: DataId,
    data: ArrayRef,
    parameters: MetadataParameters,
}

#[derive(Debug)]
pub(crate) struct DoraHandler {
    send_tx: Sender<SendRequest>,
    recv_rx: Arc<Mutex<Receiver<ReceivedArray>>>,
    recv_handle: JoinHandle<()>,
}

impl DoraHandler {
    pub(crate) fn new(log_tx: Sender<LogRequest>) -> Result<Self, BoxedError> {
        let (mut node, mut events) = DoraNode::init_from_env()?;

        let (recv_tx, recv_rx) = mpsc::channel::<ReceivedArray>();
        let (send_tx, send_rx) = mpsc::channel::<SendRequest>();

        let handler = EventHandler { log_tx, recv_tx };
        let recv_handle = thread::spawn(move || {
            while let Some(event) = events.recv() {
                if let Err(e) = handler.handle_event(event) {
                    eprintln!("Failed to handle event: {:?}", e);
                }
            }
        });

        thread::spawn(move || {
            while let Ok(req) = send_rx.recv() {
                if let Err(e) = node.send_output(req.output_id, req.parameters, req.data) {
                    eprintln!("Failed to send output: {:?}", e);
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
        let array = self.recv_rx.lock().unwrap().try_recv().ok()?;
        Some((array.input_id.into(), array.data, array.shape))
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
        self.send_tx.send(SendRequest {
            output_id: output_id.into(),
            data,
            parameters,
        })
    }
}

#[derive(Debug)]
struct ReceivedArray {
    input_id: DataId,
    data: ArrayRef,
    shape: Vec<usize>,
}

#[derive(Debug)]
struct EventHandler {
    log_tx: Sender<LogRequest>,
    recv_tx: Sender<ReceivedArray>,
}

impl EventHandler {
    fn handle_event(&self, event: Event) -> Result<(), BoxedError> {
        match event {
            Event::Input { id, data, metadata } => {
                let shape = if let Some(Parameter::ListInt(v)) = metadata.parameters.get("shape") {
                    v.iter()
                        .copied()
                        .map(usize::try_from)
                        .collect::<Result<_, _>>()?
                } else {
                    vec![data.len()]
                };

                if let (1, DataType::Float64) = (shape.len(), data.data_type()) {
                    let request = LogRequest::LogScalars {
                        path: id.clone().into(),
                        values: data.as_primitive::<Float64Type>().values().to_vec(),
                    };
                    self.log_tx.send(request)?;
                }

                self.recv_tx.send(ReceivedArray {
                    input_id: id,
                    data: data.into(),
                    shape,
                })?;
            }
            Event::Stop(_) => println!("Received stop signal from Dora."),
            _ => return Err(format!("Unhandled event: {:?}", event).into()),
        }

        Ok(())
    }
}
