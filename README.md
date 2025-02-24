# 🖼️ Etsy AI Listing Creator  

## 📌 Project Overview  
Etsy AI Listing Creator automates the creation of **printable digital art listings** for an Etsy store. It uses **AI-powered automation** to generate **images, SEO-optimized descriptions, and realistic product mockups**—eliminating the need for manual work.  

### 🚀 Key Features  
✅ AI-generated printable art (Stability AI)  
✅ Automatic SEO keyword research (Semrush API)  
✅ Image upscaling & DPI adjustment (Claid API)  
✅ Mockup creation for product display (Dynamic Mockups API)  
✅ Etsy-ready listing generation (OpenAI API)  

---

## 🏗️ Architecture  
The system follows a **sequential CrewAI workflow**, where different agents handle distinct tasks in the listing creation process.  

### **Workflow Steps**  
1️⃣ **Idea Generation** → Generate creative image concepts.  
2️⃣ **Prompt Engineering** → Craft high-quality AI prompts.  
3️⃣ **AI Image Generation** → Create an image with Stability AI.  
4️⃣ **SEO Research** → Generate title, tags, and description with Semrush.  
5️⃣ **Image Processing** → Upscale and adjust resolution (Claid API).  
6️⃣ **Mockup Generation** → Create product mockups (Dynamic Mockups API).  
7️⃣ **Listing Creation** → Compile all details into an Etsy listing.  

### **CrewAI Agents & Tasks**  
| Agent Name         | Task Description                                     | Tools Used |
|--------------------|------------------------------------------------------|------------|
| **Idea Generator**  | Brainstorm unique image concepts.                   | OpenAI API |
| **Prompt Engineer** | Convert concepts into AI prompts.                   | OpenAI API |
| **Image Generator** | Create images from prompts.                         | Stability AI |
| **SEO Researcher**  | Find best keywords & optimize description.          | Semrush API |
| **Image Processor** | Resize and set 300 DPI for print quality.           | Claid API |
| **Mockup Generator**| Generate product mockups.                           | Dynamic Mockups API |
| **Listing Generator** | Compile details into a complete Etsy listing.      | OpenAI API |

---

## 🛠️ Technology Stack  
- **[CrewAI](https://github.com/joaomdmoura/crewai)** → AI agent orchestration  
- **[OpenAI API](https://platform.openai.com/)** → Idea generation & listing creation  
- **[Stability AI](https://platform.stability.ai/)** → AI image generation  
- **[Semrush API](https://www.semrush.com/api/)** → SEO research  
- **[Claid API](https://claid.ai/)** → Image upscaling & DPI processing  
- **[Dynamic Mockups API](https://dynamicmockups.com/)** → Product mockup creation  

---

## 🔧 Installation  

### **1️⃣ Install Dependencies**  
```bash
pip install crewai crewai_tools requests openai pyyaml
```

### **2️⃣ Configure Environment Variables**  
Create a `.env` file in the root directory with your API keys:

```bash
OPENAI_API_KEY=your_openai_api_key
STABILITY_AI_KEY=your_stability_ai_key
SEMRUSH_API_KEY=your_semrush_api_key
CLAID_API_KEY=your_claid_api_key
DYNAMIC_MOCKUPS_API_KEY=your_dynamic_mockups_api_key
```

### **3️⃣ Run the Script**  
```bash
python crew.py
```

### **4️⃣ Output**  
The script will create a new Etsy listing in the `output` directory.

---

## 📝 Notes
- This project is a work in progress and will be updated with new features and improvements.
- The script is designed to be run on a local machine.


