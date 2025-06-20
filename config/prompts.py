"""
Prompt templates for circuit analysis
"""

COMPONENTS_LIST_PROMPT_MODEL1 = """
# Background #
You are an expert in digital and analog circuits. Your task is to identify the content in images of digital and analog circuits and then provide detailed and professional responses according to the objectives and requirements.

# Task Objective #
1.  Comprehensively identify all modules in the diagram that represent functional units or signal processing steps.

# Module Definition #
1.  **Basic Definition**: In a flowchart or diagram, any visually distinct node representing a specific operation or component is a module. This includes, but is not limited to:
    * **Geometric Shapes**: Triangles, circles, rectangles, rhombuses, trapezoids, ellipses, polygons, and other irregular closed shapes.
    * **Circuit Device Symbols**: Standard or non-standard circuit symbols (e.g., operational amplifiers, transistors, resistors, capacitors, etc.).
    * **Mathematical/Logical Operator Symbols**: Symbols that explicitly represent mathematical or logical operations, such as **adders/summing points (e.g., the "+" symbol in an image)**, multipliers, comparators, etc.
    * **Standard Circuit/Block Diagram Symbols (Standard Symbols)**: Recognized graphical symbols representing specific electronic functions or components. For example: a mixer with an "X" in a circle symbol (⊗), and symbols used to represent signal sources, signal sinks, signal converters, etc.

# Task Requirements #
1.  **Naming and Numbering**:
    * For modules with explicit text names, use that name directly (e.g., "H(s)", "Multi-Level Quantizer", "DAC").
    * Prioritize using the characters or text found inside the module as its name.
    * For modules without text names but with clear symbols (like the "+" symbol), name them using the format "SymbolType_Description_Number" (e.g., "Adder_1", "Summer_1").
    * For other unnamed or generic shape modules whose function is not clear, use "ShapeType_Number" (e.g., "Rectangle_1").
    * If there are multiple modules with the same name (or functionally equivalent unnamed modules that would resolve to the same base name), append a numerical suffix to differentiate them (e.g., "Filter_1", "Filter_2", "Adder_1", "Adder_2").
2.  **Module Function Description**: Provide a concise description of the main function or role of each identified module within the circuit or system.
3.  **Exclusion of Internal Connections**: This task does not require describing the input/output signal lines between modules; focus only on the modules themselves.
4.  **Output Format Rules**:
    * **Sole Output**: Your response must **only** be a valid JSON object or array.
    * **No Extra Text**: **Do not include** any explanatory text, comments, preamble, summary, or any other non-JSON characters before or after the JSON content.
    * **Strict Adherence to Structure**: The output JSON structure must exactly match the "Output Example" below.

# Output Example #
["H(s)","Adder_1"]
""".strip()

COMPONENTS_LIST_PROMPT_MODEL2 = COMPONENTS_LIST_PROMPT_MODEL1


COMPONENT_IO_PROMPT_MODEL1_v1 = """
# Role
You are a professional electronic circuit analysis AI assistant.

# Task
Your task is to analyze the specified electronic component `{component_name}` based on the provided circuit diagram context, and strictly identify all its input (inputs), output (outputs), and bidirectional (inout) connections according to the requirements.

# Definitions
- **inputs**: Pins or nodes where signals, data, or power flow into this component.
- **outputs**: Pins or nodes where signals, data, or power flow out from this component.
- **inout**: Pins or nodes that can be used as both input and output (i.e., bidirectional connections).

# Instructions
1. Precisely analyze the component named `{component_name}`.
2. Identify all relevant node names, network labels, or pin numbers connected to this component.
3. Categorize all identified connections accurately into "inputs", "outputs", or "inout" lists according to the above definitions.
4. If there are no connections in a particular category, return an empty list `[]`.

# Output Format
Your response must be and only be a properly formatted JSON object without any extra comments. It is forbidden to add any descriptive text or Markdown formatting before or after the JSON code block.
The JSON structure must be as follows:
{{
"component": "{component_name}",
"inputs": ["<node_or_pin_name_1>", "<node_or_pin_name_2>"],
"outputs": ["<node_or_pin_name_3>", "<node_or_pin_name_4>"],
"inout": ["<node_or_pin_name_5>"]
}}
""".strip()

COMPONENT_IO_PROMPT_MODEL1_v2 = """
# Role
You are a professional electronic circuit analysis AI assistant.

# Task
Your task is to analyze the specified electronic component `{component_name}` based on the provided circuit diagram context, and generate a clear, well-structured, and comprehensive description of its connections.

# Instructions
1.  Precisely locate and analyze the module named `{component_name}`.
2.  For each connection of the module, clearly state its direction (input or output), the connected module (source or destination), and the signal information (such as its purpose, frequency, or other key properties).
3.  Use a Markdown bulleted list to organize the description, ensuring the content is structured and easy to understand at a glance.
4.  Strictly follow the format and example provided below. Do not add any extraneous comments or introductory text.

# Output Format and Example
Your response must start with the component name as a title, followed by a bulleted list clearly itemizing each type of connection.

**[Format Framework]**
```markdown
### Connections of {component_name}

* **Inputs**:
    * Describe the first input connection, including the source module, signal content, and key properties
    * Describe the second input connection...
* **Outputs**:
    * Describe the first output connection, including the destination module, signal content, and key properties
    * Describe the second output connection...
""".strip()


COMPONENT_IO_PROMPT_MODEL1_v3 = """
# Role
You are an AI assistant specializing in describing connections in system block diagrams.

# Task
Your task is to analyze the specified block `{component_name}` within the provided system block diagram and generate a clear, structured, and comprehensive description of its connections. Your entire output must be based **exclusively** on the visual information (blocks, lines, arrows, and labels) present in the diagram.

# Instructions
1.  Precisely locate the block named `{component_name}`.
2.  For each line connecting to `{component_name}`, identify the other block it connects to and the label on the connecting line (if any).
3.  **CRITICAL RULE FOR CATEGORIZATION**: Your categorization of a connection MUST follow these rules:
    * If a line has an **arrow pointing TOWARDS** `{component_name}`, list it under `Inputs`.
    * If a line has an **arrow pointing AWAY FROM** `{component_name}`, list it under `Outputs`.
    * If a line has **NO ARROWHEAD** or has **arrows on both ends**, list it under `Bidirectional / Unspecified Connections`.
4.  **CRITICAL RULE FOR UNLABELED LINES**: If a connecting line has **no text label**, you MUST use the standard phrase "**Unnamed Connection**" as the line's description. **DO NOT** invent a name or describe the potential function of the line.
5.  You are strictly forbidden from using your external domain knowledge to guess or infer any information not visually present.
6.  Strictly follow the format provided below. Do not add any introductory text or extraneous comments.


# Output Format and Example
```markdown
##Connections of {component_name}
* **Inputs**:
    * ADC:Describe the first input connection, including the source module, signal content, and key properties
    * H(s):Describe the second input connection...
* **Outputs**:
    * COM_CLK:Describe the first output connection, including the destination module, signal content, and key properties
    * COM_DATA:Describe the second output connection...
* **Bidirectional**:
    * I2C Bus:Describe the first bidirectional connection...
    * SPI Bus:Describe the second bidirectional connection...
""".strip()


COMPONENT_IO_PROMPT_MODEL1 = """
# Role
You are an AI assistant specializing in describing connections in system block diagrams.

# Task
Your task is to analyze the specified block `{component_name}` within the provided system block diagram and generate a clear, structured, and comprehensive description of its connections. Your entire output must be based **exclusively** on the visual information (blocks, lines, arrows, and labels) present in the diagram.

# Instructions
1.  Precisely locate the block named `{component_name}`.
2.  For each line connecting to `{component_name}`, identify the other block it connects to and the label on the connecting line (if any).
3.  **CRITICAL RULE FOR CATEGORIZATION**: Your categorization of a connection MUST follow these rules:
    * If a line has an **arrow pointing TOWARDS** `{component_name}`, list it under `Inputs`.
    * If a line has an **arrow pointing AWAY FROM** `{component_name}`, list it under `Outputs`.
    * If a line has **NO ARROWHEAD** or has **arrows on both ends**, list it under `Bidirectional`.
4.  You are strictly forbidden from using your external domain knowledge to guess or infer any information not visually present.
5.  Strictly follow the format provided below. Do not add any introductory text or extraneous comments.

# Output Format and Example
```markdown
##Connections of {component_name}
* **Inputs**:
    * ADC:Describe connection
    * H(s):Describe connection
* **Outputs**:
    * COM_CLK:Describe connection
    * COM_DATA:Describe connection
* **Bidirectional**:
    * I2C Bus:Describe connection
    * SPI Bus:Describe connection
""".strip()


COMPONENT_IO_PROMPT_MODEL2 = COMPONENT_IO_PROMPT_MODEL1

CONSISTENCY_EVAL_PROMPT = """
I have analysis results from two different models for the same circuit diagram. 
Please evaluate whether they are consistent with each other. 
You also have access to the original circuit diagram image which you should carefully examine to make a more accurate assessment.

Model 1 Analysis:
{{model1_json}}

Model 2 Analysis:
{{model2_json}}

Evaluation steps:
1. First, check if both models' component descriptions are in valid JSON format. Extract the component_details sections.
2. If either model's output is not in proper JSON format, return {"is_consistent": false, "reason": "One or both models did not output valid JSON format for component connections"}
3. If both are in JSON format, examine the original circuit diagram image to identify the actual components and connections.
4. Compare each model's analysis with what you can observe in the image, paying special attention to:
   - Whether all components in the image are correctly identified by both models
   - Whether the connection relationships described match what you see in the image
   - Whether the functional descriptions are accurate based on the circuit design
5. Consider the analyses consistent if they both correctly identify the same components and accurately describe the connections as shown in the image, even if there are minor differences in naming or descriptions.

Please provide your evaluation as a JSON object with the following structure:
{"is_consistent": true/false, "reason": "Detailed explanation of your reasoning, pointing out specific areas of consistency or inconsistency and how they relate to what you observe in the actual circuit image"}

Return ONLY the raw JSON without any markdown formatting.
""".strip()

COMPONENT_CONSISTENCY_PROMPT_V1 = """
I have analysis results for the same component from two different models. 
Please evaluate whether their descriptions of the connections and functionality are consistent.

Component from Model 1: "{component1_name}"
Model 1 Analysis: 
{component1_details}

Matched Component from Model 2: "{component2_name}"
Model 2 Analysis: 
{component2_details}

You also have access to the original circuit diagram image to make a more accurate assessment.

Please evaluate the consistency of these component analyses by comparing:
1. The number and type of inputs/outputs described
2. The connections to other components
3. The described functionality of each connection
4. The overall role of the component in the circuit
5. If the compared context is null or empty, set is_consistent is false,set score is 0 and the reason is "The compared context is null or empty"

Provide your evaluation as a JSON object with this structure. 
Your response should be ONLY raw JSON without any markdown formatting or additional text:

{{
  "component_pair": "{component1_name}",
  "is_consistent": true/false,
  "consistency_score": 0-100,
  "inconsistencies": [
    "Description of inconsistency 1",
    "Description of inconsistency 2"
  ],
  "reasoning": "Detailed explanation of your overall consistency assessment"（用中文回答原因）
}}

If there are no inconsistencies, provide an empty array for the "inconsistencies" field. 
Remember to only return the raw JSON object without any code block formatting.
""".strip()


COMPONENT_CONSISTENCY_PROMPT = """
You are an expert AI assistant specializing in electronic circuit analysis. Your task is to perform a sophisticated consistency evaluation of two AI models' analyses for a single component, using a provided circuit diagram as the ground truth.

A key challenge is that the models might use slightly different names for connected components (e.g., Model 1 refers to "U1_ADC" while Model 2 refers to "ADC_Module"). Your evaluation must look beyond simple name matching and focus on functional equivalence.

Component from Model 1: "{component1_name}"
Model 1 Analysis: 
{component1_details}

Matched Component from Model 2: "{component2_name}"
Model 2 Analysis: 
{component2_details}

You must use the original circuit diagram image as the primary source of truth to resolve ambiguities.

Please evaluate the consistency based on the following prioritized criteria:

1.  **Functional and Structural Equivalence (Primary Criterion):**
    * **Verify against the Diagram:** Do the connections described by both models correspond to actual connections shown in the circuit diagram?
    * **Semantic Matching:** Even if the names of connected components differ, determine if they refer to the *same entity* in the diagram based on their location, function, or signal path. A connection is only "consistent" if both models describe the same link, regardless of naming.
    * **Connection/Signal Functionality:** Compare the *described purpose* of each consistent connection (e.g., "input for clock signal", "I2C data line", "5V power supply").

2.  **Overall Component Role:**
    * Based on the connections, do both models arrive at a consistent conclusion about the component's overall purpose in the circuit (e.g., "microcontroller", "power management IC", "sensor interface")?

**Scoring Methodology:**

Your final `consistency_score` will be determined by a two-step process: calculating a quantitative base score and then adjusting it based on qualitative functional analysis.

**Step 1: I/O Matching and Counting**
First, carefully analyze both models' descriptions and use the circuit diagram to match the inputs and outputs. For this step, a pin is considered "consistent" only if it is described by both models and refers to the same physical pin/function (after resolving any name differences). From this analysis, determine three key numbers:
* $N_{{\\text{{consistent}}}}$: The number of consistent inputs and outputs that are correctly matched between both models.
* $N_{{\\text{{total\\_model1}}}}$: The total number of inputs and outputs listed in the analysis for Model 1.
* $N_{{\\text{{total\\_model2}}}}$: The total number of inputs and outputs listed in the analysis for Model 2.

**Step 2: Calculate Base Score and Adjust for Final Score**
Next, calculate a quantitative `base_score` using the provided formula, which measures the structural overlap:
$$ \\text{{base\\_score}} = 100 \\times \\frac{{2 \\times N_{{\\text{{consistent}}}}}}{{N_{{\\text{{total\\_model1}}}} + N_{{\\text{{total\\_model2}}}}}} $$

Finally, **adjust this `base_score` to determine the final `consistency_score`** based on the quality of the functional descriptions (from Primary Criterion 1) and the overall role consistency (Criterion 2):
* **High Consistency(90-100):** If the functional descriptions for the consistent pins and the overall component role are highly aligned, the final score should be close to the `base_score`.
* **Moderate Inconsistency(70-89):** If there are minor but noticeable differences in the functional descriptions of some pins, slightly lower the final score from the `base_score`.
* **Major Inconsistency(0-69):** If the core function of the component or its critical pins is described in a contradictory way (e.g., one says a pin is a reset, the other says it's an output), significantly lower the final score, even if the `base_score` is high.

**Edge Case:**
* If either analysis (`component1_details` or `component2_details`) is null, empty, or clearly irrelevant, `is_consistent` must be `false`, `consistency_score` must be `0`, and the reason should be "The compared context is null or empty".

Provide your evaluation as a raw JSON object, without any markdown formatting or surrounding text.

{{
  "component_pair": "{component1_name}",
  "is_consistent": true/false,
  "consistency_score": 0-100,
  "score_details": [N_{{\\text{{consistent}}}},N_{{\\text{{total\\_model1}}}},N_{{\\text{{total\\_model2}}}},base_score],
  "better_model": "model1/model2",
  "reasoning": "（用中文回答原因。请在解释中明确展示你的计分过程，包括一致的I/O数量、两个模型的总I/O数量、计算出的base_score，以及你是如何根据功能描述的质量将base_score调整为最终分数的。）"
}}
""".strip()