# Dream Job Photo Booth: Architectural Approaches

This document outlines the two possible architectural approaches for the "Dream Job" Photo Booth project. The goal is to take a student's photo and output an image of them in their future dream job (e.g., Doctor, Engineer, Astronaut) with appropriate clothing and background.

---

## 🏗️ Approach 1: The Templates + Face Swap Approach (Current Pipeline)
**Pre-existing Templates + Replicate Face Swap**

This uses the exact same technology pipeline you are currently using for the "Foundation Day" app.

### 🔄 Workflow
1. **One-Time Preparation:** You manually find, buy, or create high-quality template images of people in different jobs (using stock photos, Midjourney, etc.). You curate a list of perfect images (e.g., Male and Female versions for 10 different jobs).
2. **Runtime Execution:** 
   * Student takes a photo at the booth.
   * Student selects their "Dream Job" (e.g., Doctor).
   * The app sends the student's photo and the pre-selected Doctor Template to **Replicate (`yan-ops/face_swap`)**.
   * Replicate seamlessly swaps the student's exact face onto the template.

### 📊 Evaluation
* **Face Likeness:** ⭐⭐⭐⭐⭐ (Perfect match, it perfectly transfers the student's actual face).
* **Cost:** **~$0.01 - $0.05 per student** (Extremely cost-effective).
* **Implementation Effort:** Very Low (You already have the code and infrastructure for this).
* **Drawback:** Every student who picks "Doctor" gets the exact same pose and background context because the template is static.

---

## 🍌 Approach 2: Direct Nano Banana Generation
**Gemini API (Image-to-Image Generation with Photo + Prompt)**

In this approach, we completely bypass predefined templates and Face Swap models. Instead, we send the student's photo directly to a Gemini model (like Gemini 2.5/3.1 Flash or Imagen 3) alongside a descriptive "Dream Job" prompt format.

### 🔄 Workflow
1. Student takes a photo at the booth.
2. Student selects their "Dream Job" (e.g., Doctor).
3. The app sends a direct API request to **Gemini (Image-to-Image)**.
   * **Input:** The student's photo (used as a reference).
   * **Prompt:** A dynamically generated text string, such as: *"A photorealistic image of this exact person working as a Doctor, wearing a white lab coat and stethoscope, standing inside a busy modern hospital, highly detailed."*
4. Gemini generates a completely unique new image from scratch based on the prompt, using the student's photo as a reference for how the person's face and features should look.

### 📊 Evaluation
* **Face Likeness:** ⭐⭐⭐ (AI models use the photo as a "reference", so it generates a person who looks *similar* to the student—like a stylized version or a close relative—but it is not a strict 1:1 topological face swap).
* **Uniqueness:** ⭐⭐⭐⭐⭐ (Every single image generated is 100% unique. Ten students picking "Doctor" will get ten different hospital backgrounds and poses).
* **Cost:** **~$0.035 - $0.14 per student** (Depending on the specific Gemini model used. It is possible to use the Free Tier for $0, subject to daily rate limits).
* **Implementation Effort:** Medium (Requires rewriting the backend API logic to handle image-plus-text prompting instead of sending two images to Replicate).
* **Technical Note:** To perform true Image-to-Image generation using Google's highest quality models (like Imagen 3), it often requires accessing the API via Google Cloud Vertex AI rather than the standard free Google AI Studio key, which requires setting up a billing account.

---

## 🏆 Summary Comparison

| Feature | 1. Templates + Face Swap | 2. Nano Banana (Photo + Prompt) |
| :--- | :--- | :--- |
| **How it works** | Paste face onto static stock photo | AI draws a new image from scratch using photo as a guide |
| **Face Likeness** | Perfect (1:1 Match) | Similar (Stylized Likeness) |
| **Uniqueness** | Low (Static Templates) | High (Unique every time) |
| **Runtime Cost/Student** | ~$0.01 - $0.05 | ~$0.035 - $0.14 (or $0 on Free Tier) |
| **Implementation** | Already Built | Needs API changes & Vertex AI integration |
