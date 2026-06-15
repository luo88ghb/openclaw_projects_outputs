import json
import requests
import uuid
import time
import os
from pathlib import Path

class ZeniPrecisionEngineV10:
    """
    Zeni_Engine_v10_Precision: Pipeline-based Pose Transfer Engine.
    Upgrades from Single-Pass to Multi-Pass (Base -> Refine) architecture.
    """
    def __init__(self, base_url="http://127.0.0.1:8188"):
        self.base_url = base_url
        self.core_path = Path(r"C:\Users\danny\.openclaw\workspace\projects\Project_Qwen2511_Pose_Transfer\Zeni_Precision_Core")
        
    def _load_workflow(self, workflow_name):
        path = self.core_path / "workflows" / workflow_name
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _queue_prompt(self, prompt):
        p = {"prompt": prompt}
        response = requests.post(f"{self.base_url}/prompt", json=p)
        return response.json().get("prompt_id")

    def _wait_for_completion(self, prompt_id):
        while True:
            res = requests.get(f"{self.base_url}/history/{prompt_id}").json()
            if prompt_id in res:
                return res[prompt_id]
            time.sleep(1)

    def _get_output_image(self, history):
        # Extract the last image from the output nodes
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                return node_output['images'][0]['filename']
        return None

    def run_precision_pipeline(self, source_image, pose_image, precision_level=1.0, **kwargs):
        """
        EXECUTION PIPELINE:
        Step 1: Base Pose Transfer (Global Pass)
        Step 2: Face Refinement (Local Pass - Kijai Style)
        """
        print(f"[Zeni-V10] Starting Precision Pipeline. Level: {precision_level}")

        # --- STAGE 1: BASE PASS ---
        print("[Zeni-V10] Stage 1/2: Executing Base Pose Transfer...")
        base_wf = self._load_workflow("base_pose_transfer.json")
        
        # Injection logic (Dynamic mapping based on config/node_mapping.json would be here)
        # For now, we simulate the target node updates
        base_wf["101"] = {"inputs": {"image": source_image}} 
        base_wf["102"] = {"inputs": {"image": pose_image}}
        
        base_id = self._queue_prompt(base_wf)
        base_history = self._wait_for_completion(base_id)
        intermediate_img = self._get_output_image(base_history)
        
        if not intermediate_img:
            raise RuntimeError("Stage 1 failed to produce an image.")

        # --- STAGE 2: REFINEMENT PASS ---
        print(f"[Zeni-V10] Stage 2/2: Executing Face Refinement (Inpainting)...")
        refine_wf = self._load_workflow("face_refinement.json")
        
        # Inject intermediate result as the input for refinement
        # Precision level controls the Denoising Strength in the JSON
        refine_wf["201"] = {"inputs": {"image": intermediate_img}} 
        refine_wf["205"] = {"inputs": {"denoise": precision_level}} 
        
        refine_id = self._queue_prompt(refine_wf)
        refine_history = self._wait_for_completion(refine_id)
        final_img = self._get_output_image(refine_history)

        print(f"[Zeni-V10] Pipeline Complete. Final Asset: {final_img}")
        return final_img

# This is a structural template. 
# In actual deployment, it will be integrated into the Streamlit app.
if __name__ == "__main__":
    print("Zeni Precision Engine v10 Loaded. Ready for Pipeline Execution.")
