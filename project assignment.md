AI-Native Engineer Assessment
Objective
Build a single-user intelligence workspace capable of learning from information over time.
The system must support two primary workflows:
Research Mode
Knowledge-Augmented Chat
The goal is to evaluate your ability to design and build an AI-native system that can acquire, structure, evolve, and utilize knowledge over time.

Workflow 1: Research Mode
The user provides a topic.
Examples:
Behavioral Economics
Urban Planning
Space Exploration
Chocolate Manufacturing
Psychology
Climate Change
The topic itself is irrelevant.
The system should autonomously:
Research the topic
Gather information
Cleanse noise
Extract knowledge
Build relationships
Update memory
Generate a synthesis

Workflow 2: Knowledge-Augmented Chat
The user should be able to:
Query the knowledge accumulated in Workflow 1
Upload additional information
Ask contextual questions
Request validation of facts
Explore relationships
Surface insights
The system should use:
Existing knowledge
Existing memory
Uploaded content
Web research (where appropriate)
to produce grounded responses.
New information should update both knowledge and memory.

Supported Inputs
Support as many of the following input types as possible:
PDF
DOCX
XLSX
Images
Audio
Video
URLs
YouTube URLs
The system should determine:
What matters
What is repetitive
What is noise
What should become knowledge
We care more about judgment than format support.

Knowledge Construction Requirements
The system must create structured knowledge.
At a minimum, demonstrate:
Entities
Relationships
Facts
Decisions
Questions
Insights
Evidence
Knowledge should persist beyond a single interaction.

Knowledge Graph Requirements
A knowledge graph is mandatory.
You may choose the implementation.
The system must demonstrate relationships between knowledge objects.
The user should be able to explore:
What do we know?
How do we know it?
What supports it?
What contradicts it?
How is it connected?
The graph should support at least one capability that would be difficult to achieve using vector retrieval alone.
Examples include:
Contradiction detection
Relationship exploration
Dependency discovery
Influence mapping
Knowledge evolution

Memory Requirements
The system must maintain memory across sessions.
New information should influence future responses.
Memory should evolve.
Memory should not merely accumulate.
The system should demonstrate:
Learning
Updating
Reinforcement
Contradiction handling
Deprecation
Example
Knowledge created in one session should influence future sessions.
Knowledge modified in later sessions should update memory.

Knowledge Evolution
Knowledge is not static.
The system should demonstrate at least one example where new information:
Reinforces existing knowledge
Modifies existing knowledge
Contradicts existing knowledge
Deprecates existing knowledge
The system should surface and explain what changed.

Autonomous Workflow Requirement
The system must demonstrate at least one autonomous workflow.
Given a topic and supporting sources, the system should independently determine:
What to process
What to ignore
What to extract
What to remember
What to surface
The user should not be required to manually orchestrate every step.

Explainability & Traceability
The system must be able to answer:
“Why did you say this?”
For any response, the user should be able to trace:
Response
 ↓
 Knowledge Used
 ↓
 Evidence Used
 ↓
 Original Sources
The system should clearly identify:
Supporting evidence
Contradicting evidence
Confidence level
Source references

Insight Generation
The system should surface both:
Obvious Insights
Clearly stated:
Facts
Decisions
Risks
Themes
Conclusions
Non-Obvious Insights
Examples include:
Patterns
Contradictions
Repeated signals
Weak connections
Emerging themes
Under-discussed risks
Relationships inferred from accumulated knowledge

Response Quality
The system should communicate intelligence clearly.
Responses should use appropriate formatting such as:
Headings
Tables
Bullets
Citations
Evidence sections
Confidence indicators
Relationship summaries
The goal is:
Decision-quality communication, not raw LLM output.

Knowledge Quality
The system should maintain metadata for knowledge where practical.
Examples include:
Confidence
Supporting evidence
Contradicting evidence
Source count
Freshness
Last updated
Knowledge quality should be visible to the user.

Noise Rejection
The system should demonstrate the ability to:
Ignore noise
Reduce duplication
Filter weak information
Prioritize stronger evidence
The system should explain why certain information was excluded.

Incremental Learning
Adding new information should not require rebuilding everything from scratch.
The system should demonstrate incremental updates where practical.

Demonstration Requirements
Your screen recording should demonstrate the following end-to-end flow:
Topic entered
Autonomous research initiated
Sources gathered
Information cleansed
Knowledge extracted
Knowledge graph updated
Memory updated
Synthesis generated
Follow-up questions asked
Responses grounded in memory
New information uploaded
Knowledge updated
Contradiction or evolution detected
Insight generation
Evidence traceability

Deliverables
The following deliverables are required:
Source Code- Github repository 
Working Application- Deployed Version - Preferably on Vercel
Architecture Diagram
Design Document
Walkthrough- Demo Like video showcasing end-to-end functionality

Documentation Requirements
In your submission, describe:
What remains unfinished
What you would improve
Technical debt
Scaling concerns
Knowledge quality concerns
Future architecture

Evaluation Focus
We are not primarily evaluating format support.
We are evaluating your ability to:
Acquire knowledge
Structure knowledge
Connect knowledge
Evolve knowledge over time
Maintain memory
Detect contradictions
Generate insights
Provide traceable, evidence-backed responses
Judgment, system design, knowledge quality, and reasoning are more important than feature count.
