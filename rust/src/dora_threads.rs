use dora_message::id::DataId;
use dora_node_api::{ArrowData, DoraNode, Event, arrow::array::ArrayRef};
use std::{
    sync::{
        Arc, Mutex,
        mpsc::{self, Receiver},
    },
    thread::{self, JoinHandle},
};

#[derive(Debug)]
pub(crate) struct DoraThreadsHandle {
    recv_rx: Arc<Mutex<Receiver<(DataId, ArrowData)>>>,
    recv_handle: JoinHandle<()>,
}

impl DoraThreadsHandle {
    pub(crate) fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let (_node, mut events) = DoraNode::init_from_env()?;

        let (recv_tx, recv_rx) = mpsc::channel::<(DataId, ArrowData)>();

        let recv_handle = thread::spawn(move || {
            while let Some(event) = events.recv() {
                match event {
                    Event::Input { id, data, .. } => {
                        if let Err(e) = recv_tx.send((id, data)) {
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

    pub(crate) fn try_recv(&self) -> Option<(String, ArrayRef)> {
        let (id, data) = self.recv_rx.lock().unwrap().try_recv().ok()?;
        Some((id.into(), data.into()))
    }

    pub(crate) fn is_running(&self) -> bool {
        !self.recv_handle.is_finished()
    }
}
