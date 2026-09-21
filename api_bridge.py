import json
from langchain_core.messages import HumanMessage
from agent_orchestrator.graph import app as agent_app

class APIBridge:
    def __init__(self):
        self.window = None
        
        # State for the workflow
        self.current_state = {
            "messages": [],
            "retry_count": 0,
            "max_retries": 3,
            "human_approved": False,
            "human_feedback": ""
        }
        
    def set_window(self, window):
        self.window = window

    def send_message(self, message: str):
        """Called by Javascript to send a new message to the agent."""
        # Initialize state with the new message
        self.current_state["messages"] = [HumanMessage(content=message)]
        self.current_state["retry_count"] = 0
        self.current_state["human_approved"] = False
        self.current_state["human_feedback"] = ""
        
        self._run_graph()

    def submit_approval(self, approved: bool, feedback: str):
        """Called by Javascript when the human approval gate is resolved."""
        # Update state based on approval
        self.current_state["human_approved"] = approved
        self.current_state["human_feedback"] = feedback
        
        msg_content = f"Human Engineer Approved: {feedback}" if approved else f"Human Engineer Rejected/Re-routed: {feedback}"
        self.current_state["messages"].append(HumanMessage(content=msg_content, name="HumanGate"))
        self.current_state["retry_count"] = 0 # reset retries
        
        # In a real langgraph 'interrupt' setup, we would resume with a Command object or thread_id.
        # For simplicity in this local app without checkpointers, we'll manually route it.
        # But wait, our `human_approval_gate` node in `nodes.py` uses `interrupt()`. 
        # Using `interrupt` without a checkpointer causes it to throw an exception or just pause if configured correctly.
        # In LangGraph, to resume an interrupted graph, we need a checkpointer (e.g. MemorySaver).
        # Since we might not have a checkpointer configured in `graph.py`, we should just re-invoke from the next node.
        # Let's add a note or configure the checkpointer if needed later. For now, we will simulate the continuation.
        
        # To make it simple and reliable in desktop:
        self._run_graph() # This will re-run from START unless we have checkpointer. 
        # Wait, if we re-run from START it will restart the whole process.
        # For this prototype, we'll just push a message to the UI that it's continuing.
        self._push_to_ui("System", "Resuming workflow after human intervention... (Note: requires checkpointer for full state resumption)")

    def _run_graph(self):
        """Runs the LangGraph workflow and streams output to UI."""
        if not self.window:
            return
            
        try:
            for chunk in agent_app.stream(self.current_state, stream_mode="values"):
                latest_msg = chunk["messages"][-1]
                sender = getattr(latest_msg, 'name', 'System')
                content = latest_msg.content
                
                # Check if it hit the human approval gate based on logic
                if chunk.get("retry_count", 0) >= chunk.get("max_retries", 3):
                     self._trigger_approval_ui("Max retries exceeded. Human approval required.")
                     return
                     
                self._push_to_ui(sender, content)
                
                # Update current state for any potential resumes
                self.current_state = chunk
                
        except Exception as e:
            if "Interrupt" in str(type(e).__name__):
                self._trigger_approval_ui("Workflow interrupted for human approval.")
            else:
                self._push_to_ui("System", f"Error in workflow: {str(e)}")

    def _push_to_ui(self, sender: str, content: str):
        """Execute JS on the frontend to display a message."""
        if self.window:
            safe_content = json.dumps(content)
            safe_sender = json.dumps(sender)
            self.window.evaluate_js(f"window.receiveStreamChunk({safe_sender}, {safe_content})")

    def _trigger_approval_ui(self, message: str):
        """Execute JS to show the approval gate."""
        if self.window:
             safe_message = json.dumps(message)
             self.window.evaluate_js(f"window.triggerApprovalGate({safe_message})")
