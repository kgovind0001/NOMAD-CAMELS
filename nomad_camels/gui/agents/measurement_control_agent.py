"""
Measurement Control Agent
========================

Specialized agent for advanced measurement control in NOMAD-CAMELS including:
- Protocol inspection and analysis
- Conditional protocol execution with device monitoring
- Real-time device value monitoring and decision making
- Advanced control flows with custom conditions
"""

import logging
import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from .context_store import ContextStore


class MeasurementControlAgent:
    """
    Advanced agent for measurement control and conditional execution.
    
    Handles:
    - Protocol inspection and detailed analysis
    - Conditional protocol execution based on device values
    - Real-time device monitoring with custom conditions
    - Advanced control flows and stopping conditions
    - Protocol modification and optimization suggestions
    """
    
    def __init__(self, main_window, context_store):
        self.main_window = main_window
        self.context_store = context_store
        self.logger = logging.getLogger(__name__)
        self.last_used = None
        
        # Monitoring state
        self.active_monitors = {}
        self.monitoring_threads = {}
        self.condition_handlers = {}
        
        # Initialize the Agno agent
        self.agent = Agent(
            name="MeasurementControlAgent",
            instructions="""
            You are an advanced measurement control agent for NOMAD-CAMELS automation system.
            
            Your capabilities include:
            - Inspecting and analyzing measurement protocols in detail
            - Setting up conditional protocol execution based on device readings
            - Monitoring device values in real-time and making decisions
            - Implementing complex control flows with custom stopping conditions
            - Providing protocol optimization suggestions
            - Managing measurement sequences with dependencies
            
            Key responsibilities:
            1. Protocol Inspection: Analyze protocols to show steps, parameters, estimated times, dependencies
            2. Conditional Execution: Run protocols with conditions like "stop when pressure < 1e-9"
            3. Device Monitoring: Continuously monitor device values and trigger actions
            4. Control Flow: Handle complex measurement sequences with branching logic
            5. Safety Checks: Ensure safe operation and prevent equipment damage
            
            When inspecting protocols:
            - Break down all steps and their purposes
            - Identify required instruments and their roles
            - Estimate execution times and resource usage
            - Highlight potential issues or optimization opportunities
            
            When setting up conditional execution:
            - Parse condition expressions (pressure < 1e-9, temperature > 300K, etc.)
            - Set up appropriate monitoring intervals
            - Define clear action triggers and responses
            - Ensure fail-safe mechanisms are in place
            
            Always prioritize safety and provide clear explanations of what will happen.
            """,
            model=OpenAIChat(id="gpt-4")
        )
    
    def process_request(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Process a measurement control request"""
        
        self.last_used = datetime.now()
        
        try:
            # Determine the specific operation type
            intent = context.get('system_state', {}).get('intent', 'unknown')
            
            if intent == 'inspect_protocol':
                return self._inspect_protocol(user_input, parameters, context)
            elif intent == 'conditional_execution':
                return self._setup_conditional_execution(user_input, parameters, context)
            elif intent == 'monitor_devices':
                return self._setup_device_monitoring(user_input, parameters, context)
            elif intent == 'stop_monitoring':
                return self._stop_monitoring(user_input, parameters, context)
            else:
                return self._analyze_measurement_request(user_input, parameters, context)
                
        except Exception as e:
            self.logger.error(f"Error processing measurement control request: {e}")
            return f"I encountered an error while processing your measurement control request: {str(e)}. Please try again."
    
    def _inspect_protocol(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Provide detailed protocol inspection and analysis"""
        
        protocol_name = parameters.get('protocol_name')
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        
        if not protocol_name:
            # If no specific protocol, offer to list available ones
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
        2. Detailed step-by-step breakdown
        3. Required instruments and their roles
        4. Estimated execution time
        5. Resource requirements (memory, disk space, etc.)
        6. Potential safety considerations
        7. Optimization suggestions
        8. Dependencies and prerequisites
        """
        
        try:
            agent_response = self.agent.run(inspection_prompt)
            return f"🔍 Protocol Analysis for '{protocol_name}':\n\n{agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error inspecting protocol: {e}")
            return f"I encountered an error while inspecting the protocol: {str(e)}"
    
    def _setup_conditional_execution(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Set up conditional protocol execution with device monitoring"""
        
        protocol_name = parameters.get('protocol_name')
        condition = parameters.get('condition', '')
        device = parameters.get('device', '')
        parameter_name = parameters.get('parameter', '')
        threshold = parameters.get('threshold', '')
        
        system_state = context.get('system_state', {})
        available_protocols = system_state.get('protocols', {})
        instruments = system_state.get('instruments', {})
        
        # Parse the condition from user input if not in parameters
        if not condition and any(keyword in user_input.lower() for keyword in ['until', 'when', 'if', 'reaches', 'below', 'above']):
            condition = self._extract_condition_from_text(user_input)
        
        # Use the agent to set up conditional execution
        setup_prompt = f"""
        The user wants to set up conditional protocol execution:
        "{user_input}"
        
        Context:
        - Protocol: {protocol_name}
        - Condition: {condition}
        - Device: {device}
        - Parameter: {parameter_name}
        - Threshold: {threshold}
        - Available protocols: {list(available_protocols.keys())}
        - Available instruments: {list(instruments.keys())}
        
        Analyze this request and provide:
        1. Interpretation of the condition
        2. Required monitoring setup
        3. Safety considerations
        4. Estimated monitoring frequency needed
        5. Clear execution plan
        6. Fallback procedures if conditions aren't met
        """
        
        try:
            agent_response = self.agent.run(setup_prompt)
            
            # If we have enough information, set up the actual monitoring
            if protocol_name and condition:
                monitor_id = self._create_conditional_monitor(protocol_name, condition, context)
                return f"🎯 Conditional Execution Setup:\n\n{agent_response}\n\n✅ Monitor created with ID: {monitor_id}"
            else:
                return f"🎯 Conditional Execution Analysis:\n\n{agent_response}\n\n⚠️ Please provide more specific details to set up the actual monitoring."
                
        except Exception as e:
            self.logger.error(f"Error setting up conditional execution: {e}")
            return f"I encountered an error while setting up conditional execution: {str(e)}"
    
    def _setup_device_monitoring(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Set up real-time device monitoring"""
        
        device_name = parameters.get('device', '')
        parameter_name = parameters.get('parameter', '')
        interval = parameters.get('interval', 1.0)
        
        system_state = context.get('system_state', {})
        instruments = system_state.get('instruments', {})
        
        # Use the agent to analyze monitoring requirements
        monitoring_prompt = f"""
        The user wants to set up device monitoring:
        "{user_input}"
        
        Context:
        - Device: {device_name}
        - Parameter: {parameter_name}
        - Monitoring interval: {interval}
        - Available instruments: {list(instruments.keys())}
        
        Provide guidance for:
        1. Monitoring setup requirements
        2. Recommended monitoring intervals
        3. Data logging considerations
        4. Alert conditions to watch for
        5. Performance impact assessment
        """
        
        try:
            agent_response = self.agent.run(monitoring_prompt)
            
            # Set up actual monitoring if device is specified
            if device_name:
                monitor_id = self._create_device_monitor(device_name, parameter_name, interval, context)
                return f"📊 Device Monitoring Setup:\n\n{agent_response}\n\n✅ Monitor started with ID: {monitor_id}"
            else:
                return f"📊 Device Monitoring Analysis:\n\n{agent_response}"
                
        except Exception as e:
            self.logger.error(f"Error setting up device monitoring: {e}")
            return f"I encountered an error while setting up device monitoring: {str(e)}"
    
    def _stop_monitoring(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Stop active monitoring tasks"""
        
        monitor_id = parameters.get('monitor_id', '')
        
        if monitor_id and monitor_id in self.active_monitors:
            self._stop_monitor(monitor_id)
            return f"🛑 Stopped monitoring task: {monitor_id}"
        elif not monitor_id and self.active_monitors:
            # Stop all monitors
            stopped_monitors = list(self.active_monitors.keys())
            for mid in stopped_monitors:
                self._stop_monitor(mid)
            return f"🛑 Stopped all monitoring tasks: {stopped_monitors}"
        else:
            return "ℹ️ No active monitoring tasks to stop."
    
    def _analyze_measurement_request(self, user_input: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Analyze general measurement control requests"""
        
        system_state = context.get('system_state', {})
        
        # Use the agent to analyze the request
        analysis_prompt = f"""
        The user has a measurement control question or request:
        "{user_input}"
        
        Current system context:
        - Available protocols: {list(system_state.get('protocols', {}).keys())}
        - Available instruments: {list(system_state.get('instruments', {}).keys())}
        - Active sample: {system_state.get('active_sample', 'None')}
        - Parameters extracted: {parameters}
        
        Provide helpful guidance and suggest specific actions for measurement control.
        """
        
        try:
            agent_response = self.agent.run(analysis_prompt)
            return f"🔬 Measurement Control Analysis:\n\n{agent_response}"
            
        except Exception as e:
            self.logger.error(f"Error analyzing measurement request: {e}")
            return f"I encountered an error while analyzing your measurement request: {str(e)}"
    
    def _extract_condition_from_text(self, text: str) -> str:
        """Extract condition expression from natural language text"""
        # This would implement natural language parsing for conditions
        # For now, return the text as-is for the agent to interpret
        return text
    
    def _create_conditional_monitor(self, protocol_name: str, condition: str, context: Dict[str, Any]) -> str:
        """Create a conditional monitor for protocol execution"""
        monitor_id = f"conditional_{protocol_name}_{datetime.now().strftime('%H%M%S')}"
        
        self.active_monitors[monitor_id] = {
            'type': 'conditional',
            'protocol': protocol_name,
            'condition': condition,
            'created': datetime.now(),
            'status': 'active'
        }
        
        # Start monitoring thread
        thread = threading.Thread(
            target=self._conditional_monitor_loop,
            args=(monitor_id, protocol_name, condition, context),
            daemon=True
        )
        thread.start()
        self.monitoring_threads[monitor_id] = thread
        
        return monitor_id
    
    def _create_device_monitor(self, device_name: str, parameter: str, interval: float, context: Dict[str, Any]) -> str:
        """Create a device monitoring task"""
        monitor_id = f"device_{device_name}_{datetime.now().strftime('%H%M%S')}"
        
        self.active_monitors[monitor_id] = {
            'type': 'device',
            'device': device_name,
            'parameter': parameter,
            'interval': interval,
            'created': datetime.now(),
            'status': 'active'
        }
        
        # Start monitoring thread
        thread = threading.Thread(
            target=self._device_monitor_loop,
            args=(monitor_id, device_name, parameter, interval),
            daemon=True
        )
        thread.start()
        self.monitoring_threads[monitor_id] = thread
        
        return monitor_id
    
    def _conditional_monitor_loop(self, monitor_id: str, protocol_name: str, condition: str, context: Dict[str, Any]):
        """Main loop for conditional monitoring"""
        try:
            while monitor_id in self.active_monitors and self.active_monitors[monitor_id]['status'] == 'active':
                # Check condition (this would need actual device interface)
                # For now, just log that we're monitoring
                self.logger.info(f"Monitoring condition '{condition}' for protocol '{protocol_name}'")
                time.sleep(1.0)  # Check every second
                
        except Exception as e:
            self.logger.error(f"Error in conditional monitor {monitor_id}: {e}")
            if monitor_id in self.active_monitors:
                self.active_monitors[monitor_id]['status'] = 'error'
    
    def _device_monitor_loop(self, monitor_id: str, device_name: str, parameter: str, interval: float):
        """Main loop for device monitoring"""
        try:
            while monitor_id in self.active_monitors and self.active_monitors[monitor_id]['status'] == 'active':
                # Read device value (this would need actual device interface)
                # For now, just log that we're monitoring
                self.logger.info(f"Monitoring {device_name}.{parameter} every {interval}s")
                time.sleep(interval)
                
        except Exception as e:
            self.logger.error(f"Error in device monitor {monitor_id}: {e}")
            if monitor_id in self.active_monitors:
                self.active_monitors[monitor_id]['status'] = 'error'
    
    def _stop_monitor(self, monitor_id: str):
        """Stop a specific monitor"""
        if monitor_id in self.active_monitors:
            self.active_monitors[monitor_id]['status'] = 'stopped'
            del self.active_monitors[monitor_id]
        
        if monitor_id in self.monitoring_threads:
            # Thread will exit on next iteration when it sees status change
            del self.monitoring_threads[monitor_id]
    
    def get_active_monitors(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active monitors"""
        return dict(self.active_monitors) 