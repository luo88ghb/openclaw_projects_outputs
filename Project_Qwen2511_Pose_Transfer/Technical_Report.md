# Technical Report: Qwen-2511 Pose Transfer (Jojo Edition)

## 1. Executive Summary
The **Qwen-2511 Pose Transfer** project implements a sophisticated image-to-image pipeline that decouples "identity/style" from "pose/structure." By utilizing a hybrid architecture combining a lightweight Streamlit UI and a heavyweight ComfyUI backend, the system allows users to project a subject's identity onto a target pose with high fidelity. The "Jojo Edition" specifically optimizes the user experience for professional "production" workflows, emphasizing prompt automation and visual consistency.

---

## 2. System Architecture

### 2.1 Functional Pipeline
The system operates on a linear data flow:
`User Input` $\rightarrow$ `Image Pre-processing` $\rightarrow$ `Feature Extraction (LLM)` $\rightarrow$ `Workflow Injection` $\rightarrow$ `Inference (ComfyUI)` $\rightarrow$ `Post-processing/Storage`.

### 2.2 Module Breakdown
- **Interface Layer (Streamlit)**: 
  - Implements a 1:1:2.5 layout for optimal screen real estate.
  - Manages session state for prompts and parameters.
  - Provides a confirmation dialog to prevent accidental high-cost compute triggers.
- **Intelligence Layer (Gemini 2.5 Pro)**: 
  - Acts as the "Visual Brain." It transforms raw image pixels into semantic descriptions.
  - **Prompt Engineering**: Uses a targeted system prompt to extract "background, lighting, atmosphere, and style" within a 150-word limit, ensuring the generated prompt is concise yet descriptive.
- **Computation Layer (ComfyUI)**: 
  - Uses a headless API approach.
  - **Workflow Injection**: The system loads `Jojo_workflow_api.json` and dynamically replaces nodes (IDs 10, 11, 12 for text; 101, 102 for images; 14, 15, 25 for parameters).
  - **Async Monitoring**: Implements a WebSocket client to listen for `executing` and `progress` events, providing a real-time telemetry feed to the user.
- **Preprocessing Engine (Pillow)**: 
  - **The Blur-Fill Algorithm**: To avoid distorting the aspect ratio of source images, the `create_padded_image_with_blur` function:
    1. Scales the image to fit the target box (512x512).
    2. Fills the remaining gaps with a scaled, Gaussian-blurred version of the same image.
    3. Pastes the original resized image on top.

---

## 3. Technical Specifications

### 3.1 Parameters & Control
| Parameter | Range | Default | Description |
| :--- | :--- | :--- | :--- |
| **Seed** | $0 \dots 2^{31}-1$ | Random | Controls the stochastic nature of the generation. |
| **CFG Scale** | $1.0 \dots 10.0$ | $1.0$ | Controls how strongly the model adheres to the prompts. |
| **Steps** | $1 \dots 40$ | $4$ | Number of denoising iterations. |
| **Longest Edge**| $512 \dots 2048$ | $1024$ | Final output resolution scaling factor. |

### 3.2 API Integration
- **Gemini API**: $\text{POST} \rightarrow \text{Base64 Image} \rightarrow \text{Text Description}$.
- **ComfyUI API**: 
  - `/prompt`: Queue task.
  - `/upload/image`: Upload source/pose assets.
  - `/history`: Retrieve final output metadata.
  - `/view`: Fetch the generated binary image.

---

## 4. Performance Analysis & Challenges
- **Latency**: The primary bottleneck is the Gemini 2.5 Pro visual analysis (handled with a 45s timeout) and the ComfyUI sampling process.
- **Fidelity**: The "Jojo" workflow is designed to maximize pose accuracy. The use of "pixel-level precision" instructions in `p2` ensures the model prioritizes the pose reference over the subject's original posture.
- **Reliability**: The integration of a "Core Engine Alive" check in the sidebar prevents the application from attempting to queue tasks when the backend is offline.

## 5. Conclusion & Future Work
The current iteration successfully automates the tedious aspects of pose transfer (prompting and padding). Future enhancements will focus on:
1. **Multi-Pose Batching**: Allowing multiple pose references in a single run.
2. **Refined Masking**: implementing automated segmentation to better isolate the subject from the background during transfer.
3. **Cloud Deployment**: Moving from `127.0.0.1` to a remote GPU cluster.
