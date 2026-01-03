"""
Agentic AI Core - The brain of our autonomous data analysis agent
"""

import json
import anthropic
from typing import List, Dict, Any, Optional
from django.conf import settings


class AgenticAI:
    """
    Agentic AI that autonomously analyzes data, makes decisions,
    and generates comprehensive reports through iterative reasoning
    """
    
    def __init__(self, user_query: str, dataset_context: Optional[Dict] = None):
        self.user_query = user_query
        self.dataset_context = dataset_context or {}
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.conversation_history = []
        self.reasoning_trace = []
        self.tools_used = []
        self.findings = {}
        
    def run(self) -> Dict[str, Any]:
        """
        Main agentic loop - agent decides what to investigate and how
        """
        # Step 1: Planning phase
        plan = self._create_analysis_plan()
        self.reasoning_trace.append({
            'phase': 'planning',
            'content': plan
        })
        
        # Step 2: Investigation phase (iterative)
        investigation_complete = False
        iteration = 0
        max_iterations = settings.MAX_AGENT_ITERATIONS
        
        while not investigation_complete and iteration < max_iterations:
            iteration += 1
            
            # Agent decides next action
            next_action = self._decide_next_action(plan, iteration)
            
            if next_action['action'] == 'complete':
                investigation_complete = True
                break
            
            # Execute the action
            result = self._execute_action(next_action)
            
            # Store findings
            self.findings[f"iteration_{iteration}"] = result
            self.reasoning_trace.append({
                'phase': 'investigation',
                'iteration': iteration,
                'action': next_action,
                'result': result
            })
            
            # Agent reflects on results and decides if more investigation needed
            if self._should_continue_investigation(result, iteration):
                continue
            else:
                investigation_complete = True
        
        # Step 3: Synthesis phase
        final_report = self._synthesize_report()
        
        return {
            'report': final_report,
            'reasoning_trace': self.reasoning_trace,
            'tools_used': self.tools_used,
            'findings': self.findings
        }
    
    def _create_analysis_plan(self) -> Dict[str, Any]:
        """Agent creates its own analysis plan based on query and data"""
        
        system_prompt = """You are an expert data analyst AI agent. Given a user query and dataset context, 
        create a comprehensive analysis plan. Think step-by-step about what investigations would be most valuable.
        
        Return your plan as JSON with:
        - main_objective: Clear statement of what user wants to know
        - key_questions: List of specific questions to answer
        - analysis_approach: High-level strategy
        - potential_tools: Tools/methods you might use
        """
        
        user_message = f"""
        User Query: {self.user_query}
        
        Dataset Context:
        {json.dumps(self.dataset_context, indent=2)}
        
        Create an analysis plan.
        """
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        plan_text = response.content[0].text
        
        # Try to extract JSON, fallback to text
        try:
            plan = json.loads(plan_text)
        except:
            plan = {"raw_plan": plan_text}
        
        return plan
    
    def _decide_next_action(self, plan: Dict, iteration: int) -> Dict[str, Any]:
        """Agent decides what to investigate next"""
        
        context = f"""
        Analysis Plan: {json.dumps(plan, indent=2)}
        
        Current Iteration: {iteration}
        
        Previous Findings: {json.dumps(self.findings, indent=2)}
        
        Dataset Available: {json.dumps(self.dataset_context, indent=2)}
        """
        
        system_prompt = """You are an autonomous data analysis agent. Based on your plan and previous findings,
        decide the NEXT specific action to take. Be strategic - follow leads, dig deeper into anomalies.
        
        Return JSON with:
        - action: "analyze", "calculate", "compare", "investigate_anomaly", or "complete"
        - target: What specifically to analyze
        - method: How to analyze it
        - reasoning: Why this is the next best step
        """
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": context}]
        )
        
        try:
            action = json.loads(response.content[0].text)
        except:
            action = {
                "action": "complete",
                "reasoning": "Unable to parse action, completing analysis"
            }
        
        return action
    
    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the decided action"""
        
        action_type = action.get('action', 'analyze')
        
        # This is where you'd call actual analysis tools
        # For now, we'll simulate with LLM-based analysis
        
        if action_type == 'analyze':
            result = self._perform_analysis(action)
        elif action_type == 'calculate':
            result = self._perform_calculation(action)
        elif action_type == 'compare':
            result = self._perform_comparison(action)
        elif action_type == 'investigate_anomaly':
            result = self._investigate_anomaly(action)
        else:
            result = {"status": "unknown_action"}
        
        self.tools_used.append(action_type)
        return result
    
    def _perform_analysis(self, action: Dict) -> Dict[str, Any]:
        """Perform data analysis based on action"""
        
        prompt = f"""
        Analyze the following based on the action:
        
        Action: {json.dumps(action, indent=2)}
        Dataset Context: {json.dumps(self.dataset_context, indent=2)}
        Previous Findings: {json.dumps(self.findings, indent=2)}
        
        Provide specific analytical insights in JSON format with:
        - insight: Main finding
        - data_points: Key data points discovered
        - significance: Why this matters
        - next_steps: What this suggests we should investigate next (if anything)
        """
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            return json.loads(response.content[0].text)
        except:
            return {"insight": response.content[0].text}
    
    def _perform_calculation(self, action: Dict) -> Dict[str, Any]:
        """Perform calculations"""
        # Implement specific calculations
        return {"calculation": "performed", "action": action}
    
    def _perform_comparison(self, action: Dict) -> Dict[str, Any]:
        """Compare data segments"""
        # Implement comparison logic
        return {"comparison": "completed", "action": action}
    
    def _investigate_anomaly(self, action: Dict) -> Dict[str, Any]:
        """Deep dive into anomalies"""
        # Implement anomaly investigation
        return {"anomaly_investigation": "completed", "action": action}
    
    def _should_continue_investigation(self, result: Dict, iteration: int) -> bool:
        """Agent decides if more investigation is needed"""
        
        if iteration >= settings.MAX_AGENT_ITERATIONS - 1:
            return False
        
        # Ask agent if it needs to continue
        prompt = f"""
        Based on this result: {json.dumps(result, indent=2)}
        
        And previous findings: {json.dumps(self.findings, indent=2)}
        
        Original query: {self.user_query}
        
        Have we answered the user's question comprehensively? 
        Respond with JSON: {{"continue": true/false, "reasoning": "why"}}
        """
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            decision = json.loads(response.content[0].text)
            return decision.get('continue', False)
        except:
            return False
    
    def _synthesize_report(self) -> str:
        """Synthesize all findings into comprehensive report"""
        
        system_prompt = """You are a senior data analyst creating a comprehensive report.
        Synthesize all the investigation findings into a clear, actionable report.
        
        Structure:
        1. Executive Summary
        2. Key Findings (with data points)
        3. Detailed Analysis
        4. Insights & Implications
        5. Recommendations
        
        Be specific, cite data, and provide actionable insights."""
        
        synthesis_context = f"""
        Original Query: {self.user_query}
        
        Analysis Plan: {json.dumps(self.reasoning_trace[0], indent=2)}
        
        All Findings: {json.dumps(self.findings, indent=2)}
        
        Tools Used: {self.tools_used}
        
        Dataset Context: {json.dumps(self.dataset_context, indent=2)}
        
        Create the final comprehensive report.
        """
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": synthesis_context}]
        )
        
        return response.content[0].text


class SimpleResponseAgent:
    """Simple agent for non-analytical queries"""
    
    def __init__(self, user_query: str, context: Optional[str] = None):
        self.user_query = user_query
        self.context = context
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def respond(self) -> str:
        """Generate simple response"""
        
        system_prompt = """You are a helpful AI assistant for data analysis. 
        Respond naturally and helpfully to user queries."""
        
        messages = []
        if self.context:
            messages.append({
                "role": "assistant",
                "content": self.context
            })
        
        messages.append({
            "role": "user",
            "content": self.user_query
        })
        
        response = self.client.messages.create(
            model=settings.DEFAULT_LLM_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=messages
        )
        
        return response.content[0].text