"""
Protocol Agent
=============

Specialized agent for handling protocol-related operations in NOMAD-CAMELS.
Enhanced with protocol inspection and advanced control capabilities.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from .context_store import ContextStore


class ProtocolAgent:
    """
    Agent specialized in protocol management and execution.
    
    Handles:
    - Protocol execution
    - Protocol listing and information
    - Protocol inspection and analysis
    - Protocol configuration
    - Measurement guidance
    - Integration with measurement control
    """
    
    def __init__(self, main_window, context_store):
        self.main_window = main_window
        self.context_store = context_store
        self.logger = logging.getLogger(__name__)
        self.last_used = None
        
        # Initialize the Agno agent
        self.agent = Agent(
            name="ProtocolAgent",
            instructions="""
            You are a specialized agent for managing protocols in NOMAD-CAMELS measurement automation system.
            
            Your capabilities include:
            - Executing measurement protocols
            - Listing available protocols with detailed information
            - Inspecting protocol structure and requirements
            - Providing protocol information and guidance
            - Helping with protocol configuration
            - Monitoring protocol execution status
            - Analyzing protocol compatibility and dependencies
            
            Always:
            1. Ensure instruments are properly configured before protocol execution
            2. Provide clear status updates during measurements
            3. Handle errors gracefully and suggest solutions
            4. Validate protocol parameters before execution
            5. Maintain measurement data integrity
            6. Offer protocol optimization suggestions
            
            When executing protocols, check that all required instruments are available and configured.
            When listing protocols, provide relevant details about each protocol's purpose and requirements.
            When inspecting protocols, provide comprehensive analysis including steps, timing, and dependencies.
            Always prioritize safety and provide clear explanations of what will happen.
            """,
            model=OpenAIChat(id="gpt-4")
        )
    
    def process_request(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Process a protocol-related request"""
        
        self.last_used = datetime.now()
        
        try:
            # Determine the specific protocol operation
            intent = context.get('system_state', {}).get('intent', 'unknown')
            
            # If intent is not in system_state, check if it's in the main context
            if intent == 'unknown':
                # Try to get intent from conversation context or detect it from user input
                conv_history = context.get('conversation_history', [])
                if conv_history:
                    intent = conv_history[-1].get('intent', 'unknown')
                
                # Fallback: detect intent from user input
                if intent == 'unknown':
                    user_lower = user_input.lower()
                    if any(word in user_lower for word in ['list', 'show', 'provide']) and any(phrase in user_lower for phrase in ['protocol', 'measurement protocol', 'protocols']):
                        intent = 'list_protocols'
                    elif any(word in user_lower for word in ['run', 'execute', 'start']):
                        intent = 'run_protocol'
                    elif any(word in user_lower for word in ['inspect', 'analyze', 'examine']):
                        intent = 'inspect_protocol'
            
            self.logger.info(f"Processing protocol request with intent: {intent}")
            
            if intent == 'run_protocol':
                return self._run_protocol(user_input, parameters, context)
            elif intent == 'list_protocols':
                return self._list_protocols(user_input, parameters, context)
            elif intent == 'inspect_protocol':
                return self._inspect_protocol(user_input, parameters, context)
            elif intent == 'protocol_status':
                return self._get_protocol_status(user_input, parameters, context)
            else:
                return self._general_protocol_query(user_input, parameters, context)
                
        except Exception as e:
            self.logger.error(f"Error processing protocol request: {e}")
            return f"I encountered an error while processing your protocol request: {str(e)}. Please try again."
    
    def _run_protocol(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Execute a measurement protocol"""
        
        protocol_name = parameters.get('protocol_name')
        
        if not protocol_name:
            return "I need a protocol name to execute. Which protocol would you like to run?"
        
        # Get current system state
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        active_sample = system_state.get('active_sample', 'None')
        instruments = system_state.get('instruments', {})
        
        # Check if protocol exists
        if protocol_name not in available_protocols:
            return f"Protocol '{protocol_name}' not found. Available protocols: {list(available_protocols.keys())}"
        
        # Use the agent to guide protocol execution
        execution_prompt = f"""
        The user wants to execute protocol '{protocol_name}':
        "{user_input}"
        
        Current context:
        - Active sample: {active_sample}
        - Available instruments: {list(instruments.keys())}
        - Protocol details: {available_protocols.get(protocol_name, {})}
        
        Provide guidance for protocol execution, including:
        1. Pre-execution checks
        2. Required instruments and their status
        3. Estimated execution time
        4. Any warnings or considerations
        5. Recommendations for conditional execution if applicable
        """
        
        try:
            agent_response = self.agent.run(execution_prompt)
            
            # Check if we can actually execute the protocol
            if self._can_execute_protocol(protocol_name, context):
                # Try to actually start the protocol execution
                if hasattr(self.main_window, 'run_protocol'):
                    self.main_window.run_protocol(protocol_name)
                    return f"🔬 Starting protocol '{protocol_name}':\n{agent_response}\n\n✅ Protocol execution initiated!"
                else:
                    return f"🔬 Protocol '{protocol_name}' ready to start:\n{agent_response}\n\n⚠️ Please use the main interface to start execution."
            else:
                return f"⚠️ Cannot execute protocol '{protocol_name}' right now:\n{agent_response}"
                
        except Exception as e:
            self.logger.error(f"Error in protocol execution: {e}")
            return f"I encountered an error while preparing to execute the protocol: {str(e)}"
    
    def _inspect_protocol(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Provide detailed protocol inspection"""
        
        protocol_name = parameters.get('protocol_name')
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        
        if not protocol_name:
            if available_protocols:
                return f"📋 I can inspect any of these protocols: {list(available_protocols.keys())}. Which one would you like to analyze?"
            else:
                return "📋 No protocols are currently loaded. Please load a protocol first."
        
        if protocol_name not in available_protocols:
            return f"❌ Protocol '{protocol_name}' not found. Available protocols: {list(available_protocols.keys())}"
        
        protocol_data = available_protocols[protocol_name]
        
        # Use the agent to provide detailed analysis
        inspection_prompt = f"""
        The user wants to inspect protocol '{protocol_name}':
        "{user_input}"
        
        Protocol data: {protocol_data}
        Available instruments: {list(system_state.get('instruments', {}).keys())}
        Current sample: {system_state.get('active_sample', 'None')}
        
        Provide a comprehensive protocol analysis including:
        1. Protocol overview and purpose
        2. Step-by-step breakdown of the measurement sequence
        3. Required instruments and their specific roles
        4. Expected data outputs and formats
        5. Estimated execution time and resource usage
        6. Safety considerations and potential risks
        7. Prerequisites and dependencies
        8. Suggestions for optimization or modifications
        9. Compatibility with conditional execution features
        """
        
        try:
            agent_response = self.agent.run(inspection_prompt)
            return f"🔍 Protocol Analysis for '{protocol_name}':\n\n{agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error inspecting protocol: {e}")
            return f"I encountered an error while inspecting the protocol: {str(e)}"
    
    def _get_protocol_status(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Get current protocol execution status"""
        
        system_state = context.get('system_state', {})
        
        # Check if a protocol is currently running
        protocol_running = system_state.get('protocol_running', False)
        current_protocol = system_state.get('current_protocol', None)
        execution_progress = system_state.get('execution_progress', 0)
        
        status_prompt = f"""
        The user wants to check protocol status:
        "{user_input}"
        
        Current status:
        - Protocol running: {protocol_running}
        - Current protocol: {current_protocol}
        - Execution progress: {execution_progress}%
        - Available protocols: {list(system_state.get('protocols', {}).keys())}
        
        Provide a clear status report and suggest next actions if appropriate.
        """
        
        try:
            agent_response = self.agent.run(status_prompt)
            return f"📊 Protocol Status:\n\n{agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error getting protocol status: {e}")
            return f"I encountered an error while checking protocol status: {str(e)}"
    
    def _can_execute_protocol(self, protocol_name: str, context: Dict[str, Any]) -> bool:
        """Check if protocol can be executed"""
        
        system_state = context.get('system_state', {})
        
        # Check if there's an active sample
        if system_state.get('active_sample') == 'None':
            return False
        
        # Check if another protocol is already running
        if system_state.get('protocol_running', False):
            return False
        
        # Check if required instruments are available
        # This would need to be implemented based on protocol requirements
        
        return True
    
    def _list_protocols(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """List available protocols with detailed information"""
        
        # Get current system state
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        
        # Log for debugging
        self.logger.info(f"Listing protocols. Found {len(available_protocols)} protocols: {list(available_protocols.keys())}")
        
        if not available_protocols:
            return """📋 **No measurement protocols found.**

This could be because:
1. **No protocols have been loaded yet** - Protocols need to be loaded from files or created
2. **The system is still initializing** - Please wait a moment and try again
3. **Protocols are stored elsewhere** - Check if protocols are loaded in the main interface

**To load or create protocols:**

🔧 **Loading existing protocols:**
- Go to **File → Load Protocol** in the main menu
- Navigate to your protocol files (usually `.json` or `.camels` files)
- Select and load your measurement protocols

🔧 **Creating new protocols:**
- Use the **Protocol Builder** in the main interface
- Define measurement steps, instruments, and parameters
- Save your protocol for future use

🔧 **Importing protocols:**
- Import protocols from previous NOMAD-CAMELS sessions
- Load protocol templates from the examples folder

📝 **Need help?** Ask me:
- "How do I create a new protocol?"
- "How do I load existing protocols?"
- "Show me protocol examples"

Would you like guidance on any of these options?"""
        
        # Use the agent to format the protocol list
        list_prompt = f"""
        The user wants to see the protocol list:
        "{user_input}"
        
        Available protocols: {available_protocols}
        Current system context:
        - Active sample: {system_state.get('active_sample', 'None')}
        - Available instruments: {list(system_state.get('instruments', {}).keys())}
        
        Format this information in a user-friendly way, showing:
        1. Protocol names and descriptions
        2. Key requirements for each protocol
        3. Estimated execution times (if available)
        4. Compatibility with current setup
        5. Recommended use cases
        
        Present this as a numbered list with clear formatting.
        """
        
        try:
            agent_response = self.agent.run(list_prompt)
            return f"📋 **Available Protocols ({len(available_protocols)} found):**\n\n{agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error listing protocols: {e}")
            # Fallback to simple listing if AI agent fails
            protocol_list = "\n".join([f"• {name}" for name in available_protocols.keys()])
            return f"📋 **Available Protocols ({len(available_protocols)} found):**\n\n{protocol_list}\n\nNote: Error occurred while getting detailed information: {str(e)}"
    
    def _general_protocol_query(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle general protocol-related queries"""
        
        # Get current system state
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        
        # Use the agent to handle the general query
        query_prompt = f"""
        The user has a general protocol-related question:
        "{user_input}"
        
        Current context:
        - Available protocols: {list(available_protocols.keys())}
        - Parameters extracted: {parameters}
        - Active sample: {system_state.get('active_sample', 'None')}
        - Available instruments: {list(system_state.get('instruments', {}).keys())}
        
        Provide a helpful response and suggest specific actions if appropriate.
        Consider whether this query might benefit from:
        1. Protocol inspection capabilities
        2. Conditional execution features
        3. Device monitoring
        4. Protocol modification suggestions
        """
        
        try:
            agent_response = self.agent.run(query_prompt)
            return f"🔬 Protocol Information: {agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error handling protocol query: {e}")
            return f"I encountered an error while processing your protocol query: {str(e)}" 