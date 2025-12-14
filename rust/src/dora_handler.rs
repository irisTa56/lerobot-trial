use dora_message::id::DataId;
use dora_node_api::{ArrowData, DoraNode, Event, Metadata, Parameter, arrow::array::ArrayRef};
use std::{
    sync::{
        Arc, Mutex,
        mpsc::{self, Receiver},
    },
    thread::{self, JoinHandle},
};

type BoxedError = Box<dyn std::error::Error>;

#[derive(Debug)]
pub(crate) struct DoraHandler {
    recv_rx: Arc<Mutex<Receiver<(DataId, ArrowData, Metadata)>>>,
    recv_handle: JoinHandle<()>,
}

impl DoraHandler {
    pub(crate) fn new() -> Result<Self, BoxedError> {
        let (_node, mut events) = DoraNode::init_from_env()?;

        let (recv_tx, recv_rx) = mpsc::channel();

        let recv_handle = thread::spawn(move || {
            while let Some(event) = events.recv() {
                match event {
                    Event::Input { id, data, metadata } => {
                        if let Err(e) = recv_tx.send((id, data, metadata)) {
                            eprintln!("Failed to send received data: {:?}", e);
                        }
                    }
                    Event::Stop(_) => println!("Received stop signal from Dora."),
                    _ => eprintln!("Unexpected event: {:?}", event),
                }
            }
        });

        Ok(Self {
            recv_rx: Arc::new(Mutex::new(recv_rx)),
            recv_handle,
        })
    }

    pub(crate) fn try_recv(&self) -> Option<(String, ArrayRef, Vec<usize>)> {
        let (id, data, metadata) = self.recv_rx.lock().unwrap().try_recv().ok()?;
        let shape = metadata
            .parameters
            .get("shape")
            .and_then(|param| match param {
                Parameter::ListInt(v) => v.iter().map(|i| usize::try_from(*i).ok()).collect(),
                _ => None,
            })
            .unwrap_or_else(|| vec![data.len()]);
        Some((id.into(), data.into(), shape))
    }

    pub(crate) fn is_running(&self) -> bool {
        !self.recv_handle.is_finished()
    }
}
