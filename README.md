# 🖼️ Etsy AI Listing Creator

## 📌 Project Overview

Etsy AI Listing Creator automates the creation of **printable digital art listings** for an Etsy store. It uses **AI-powered automation** to generate **images, SEO-optimized descriptions, and realistic product mockups**—eliminating the need for manual work. The system intelligently handles both portrait and landscape aspect ratios throughout the entire workflow.

### 🚀 Key Features

✅ AI-generated printable art (Replicate AI)  
✅ Automatic aspect ratio detection and handling  
✅ Intelligent file organization system  
✅ Image upscaling & DPI adjustment for print-ready files  
✅ Mockup creation with aspect ratio awareness  
✅ SEO-optimized listing content  
✅ Complete Etsy-ready listing generation

---

## 🏗️ Architecture

The system follows a **sequential CrewAI workflow**, where different agents handle distinct tasks in the listing creation process.

### **Workflow Steps**

1️⃣ **Concept Generation** → Generate creative art concepts with aspect ratio determination.  
2️⃣ **Prompt Engineering** → Craft high-quality AI prompts with aspect ratio preservation.  
3️⃣ **AI Image Generation** → Create an image with Replicate AI using the specified aspect ratio.  
4️⃣ **SEO Research** → Generate title, tags, and description optimized for Etsy search.  
5️⃣ **Image Processing** → Create multiple print-ready versions in standard sizes based on aspect ratio.  
6️⃣ **Mockup Generation** → Create product mockups with templates matched to the aspect ratio.  
7️⃣ **Listing Creation** → Organize files and compile all details into a complete Etsy listing.

### **CrewAI Agents & Tasks**

| Agent Name           | Task Description                                                 | Tools Used                      |
| -------------------- | ---------------------------------------------------------------- | ------------------------------- |
| **Idea Generator**   | Generate unique concepts with aspect ratio determination.        | OpenAI API                      |
| **Prompt Engineer**  | Convert concepts into AI prompts with aspect ratio preservation. | OpenAI API                      |
| **Image Generator**  | Create images from prompts using specified aspect ratio.         | ReplicateTool                   |
| **SEO Researcher**   | Find best keywords & optimize description.                       | OpenAI API, JsonSaveTool        |
| **Image Processor**  | Create multiple print-ready versions based on aspect ratio.      | ImageProcessingTool             |
| **Mockup Generator** | Generate product mockups with aspect ratio-aware templates.      | DynamicMockupTool               |
| **Listing Creator**  | Organize files and compile details into a complete Etsy listing. | FileOrganizerTool, JsonSaveTool |

### **Tools**

| Tool Name               | Description                                                           |
| ----------------------- | --------------------------------------------------------------------- |
| **ReplicateTool**       | Generates images using Replicate AI with aspect ratio support.        |
| **ImageProcessingTool** | Creates print-ready versions in standard sizes based on aspect ratio. |
| **DynamicMockupTool**   | Creates product mockups with templates matched to the aspect ratio.   |
| **JsonSaveTool**        | Saves JSON data to files with support for subdirectories.             |
| **FileOrganizerTool**   | Organizes files into a structured directory system.                   |

---

## 📁 File Organization

The system creates a structured directory for each listing:

```
listing_name_timestamp/
├── concept/
│   └── concept.json
├── original/
│   └── original_image.png
├── prints/
│   ├── print_4x6.png
│   ├── print_5x7.png
│   ├── print_8x10.png
│   ├── print_11x14.png
│   └── print_16x20.png
├── mockups/
│   ├── mockup_frame.png
│   ├── mockup_wall.png
│   └── mockup_room.png
├── metadata/
│   ├── seo.json
│   └── listing.json
└── manifest.json
```

---

## 🛠️ Technology Stack

- **[CrewAI](https://github.com/joaomdmoura/crewai)** → AI agent orchestration
- **[OpenAI API](https://platform.openai.com/)** → Idea generation & listing creation
- **[Replicate AI](https://replicate.com/)** → AI image generation
- **[Dynamic Mockups API](https://app.dynamicmockups.com/dashboard-api/)** → Generate mockups
- **[Pillow](https://python-pillow.org/)** → Image processing
- **[PyYAML](https://pyyaml.org/)** → Configuration management

---

## 🔧 Installation

### **1️⃣ Install Dependencies**

```bash
pip install -r requirements.txt
```

### **2️⃣ Configure Environment Variables**

Create a `.env` file in the root directory with your API keys:

```bash
# Required API keys
OPENAI_API_KEY=your_openai_api_key                       # Required for AI agents (idea generation, prompt engineering, SEO)
REPLICATE_API_TOKEN=your_replicate_api_token             # Required for image generation
IMGBB_API_KEY=your_imgbb_api_key                         # Required For uploading images to ImgBB (used by ReplicateTool)
DYNAMIC_MOCKUPS_API_KEY=your_dynamic_mockups_api_key     # Required for creating makeups           
```


### **3️⃣ Run the Script**

```bash
python -m src.etsy_listing_creator.crew
```

### **4️⃣ Output**

The script will create a new organized directory with all listing files in the `output` directory.

---

## 📝 Notes

- The system intelligently handles both portrait (2:3) and landscape (3:2) aspect ratios.
- Print sizes are automatically adjusted based on the aspect ratio.
- All files are organized into a structured directory system for easy management.
- The workflow is designed to be run in sequence, with each step building on the previous one.
