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
✅ User approval workflow for concepts and images

---

## 🏗️ Architecture

The system follows a **sequential CrewAI workflow**, where different agents handle distinct tasks in the listing creation process.

### **Workflow Steps**

1️⃣ **Concept Generation** → Generate creative art concepts with aspect ratio determination and user approval.  
2️⃣ **Prompt Engineering** → Craft high-quality AI prompts with aspect ratio preservation and JSON saving.  
3️⃣ **AI Image Generation** → Create an image with Replicate AI using the specified aspect ratio and user approval.  
4️⃣ **SEO Research** → Generate title, tags, and description optimized for Etsy search using the prompt engineer's output.  
5️⃣ **Image Processing** → Create multiple print-ready versions in standard sizes based on aspect ratio.  
6️⃣ **Mockup Generation** → Create product mockups with templates matched to the aspect ratio.  
7️⃣ **Listing Creation** → Organize files and compile all details into a complete Etsy listing.

### **CrewAI Agents & Tasks**

| Agent Name           | Task Description                                                                 | Tools Used                      |
| -------------------- | -------------------------------------------------------------------------------- | ------------------------------- |
| **Idea Generator**   | Generate unique concepts with aspect ratio determination and user approval.      | OpenAI API, JsonSaveTool        |
| **Prompt Engineer**  | Convert concepts into AI prompts with aspect ratio preservation and JSON saving. | OpenAI API, JsonSaveTool        |
| **Image Generator**  | Create images from prompts using specified aspect ratio with user approval.      | ReplicateTool                   |
| **SEO Researcher**   | Find best keywords & optimize description using prompt engineer's output.        | OpenAI API, JsonSaveTool        |
| **Image Processor**  | Create multiple print-ready versions based on aspect ratio.                      | ImageProcessingTool             |
| **Mockup Generator** | Generate product mockups with aspect ratio-aware templates.                      | DynamicMockupTool               |
| **Listing Creator**  | Organize files and compile details into a complete Etsy listing.                 | FileOrganizerTool, JsonSaveTool |

### **Tools**

| Tool Name               | Description                                                                            |
| ----------------------- | -------------------------------------------------------------------------------------- |
| **ReplicateTool**       | Generates images using Replicate AI with aspect ratio support and user approval.       |
| **ImageProcessingTool** | Creates print-ready versions in standard sizes based on aspect ratio.                  |
| **DynamicMockupTool**   | Creates product mockups with templates matched to the aspect ratio.                    |
| **JsonSaveTool**        | Saves JSON data to files with support for subdirectories and handles concept approval. |
| **FileOrganizerTool**   | Organizes files into a structured directory system.                                    |

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

## 📋 Requirements

- Python 3.10 or higher
- Internet connection for API access
- API keys for OpenAI, Replicate, ImgBB, and Dynamic Mockups

---

## 🔧 Installation

### **1️⃣ Clone the Repository**

First, clone the repository to your local machine:

```bash
# Clone the repository
git clone https://github.com/orizehavi97/etsy-listing-creator.git

# Navigate to the project directory
cd etsy-listing-creator
```

### **2️⃣ Set Up Virtual Environment**

It's recommended to use a virtual environment to avoid conflicts with other Python packages:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### **3️⃣ Install Dependencies**

```bash
pip install -r requirements.txt
```

### **4️⃣ Configure Environment Variables**

Create a `.env` file in the root directory with your API keys:

```bash
# Required API keys
OPENAI_API_KEY=your_openai_api_key                       # Required for AI agents (idea generation, prompt engineering, SEO)
REPLICATE_API_TOKEN=your_replicate_api_token             # Required for image generation
IMGBB_API_KEY=your_imgbb_api_key                         # Required For uploading images to ImgBB (used by ReplicateTool)
DYNAMIC_MOCKUPS_API_KEY=your_dynamic_mockups_api_key     # Required for creating makeups
```

### **5️⃣ Run the Script**

```bash
python -m src.etsy_listing_creator.crew
```

### **6️⃣ Output**

The script will create a new organized directory with all listing files in the `output` directory.

---

## 📝 Notes

- The system intelligently handles both portrait (3:4) and landscape (4:3) aspect ratios.
- Print sizes are automatically adjusted based on the aspect ratio.
- All files are organized into a structured directory system for easy management.
- The workflow is designed to be run in sequence, with each step building on the previous one.
- User approval is required for both concept generation and image generation.
- If a concept or image is rejected, the system will automatically generate a new one until approved.
- The image generator returns a JSON string containing both the image path and aspect ratio.

## 🔄 Batch Processing

The system supports batch processing to generate multiple listings in a single run. This feature allows you to:

- Generate a specified number of listings (e.g., 30) in sequence
- Each listing goes through the complete workflow with user approval at key steps
- All listings are organized in separate directories with consistent structure
- Efficiently scale your Etsy store with multiple unique listings

This is ideal for quickly populating your Etsy store with a variety of high-quality, unique digital art listings.

## 🔍 Troubleshooting

### Common Issues

1. **API Key Errors**

   - Ensure all API keys are correctly set in your `.env` file
   - Check that there are no extra spaces or quotes around your API keys
   - Verify your API keys are still valid and have not expired

2. **Image Generation Issues**

   - If image generation fails, check your Replicate API token
   - Ensure you have sufficient credits on your Replicate account
   - Try regenerating with a different prompt if specific prompts consistently fail

3. **Virtual Environment Problems**

   - If you encounter module import errors, ensure your virtual environment is activated
   - Try reinstalling dependencies with `pip install -r requirements.txt --force-reinstall`
   - Make sure you're using Python 3.10 or higher

4. **File Permission Errors**
   - Ensure the application has write permissions to the output directory
   - Close any applications that might be using the files in the output directory

### Getting Help

If you encounter issues not covered here, please:

1. Check the logs for specific error messages
2. Search for the error message in the project's issues on GitHub
3. Open a new issue with detailed information about the problem if it hasn't been reported

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Here's how you can contribute to the project:

### Reporting Issues

- Use the GitHub issue tracker to report bugs
- Describe the bug in detail including steps to reproduce
- Include information about your environment (OS, Python version, etc.)

### Feature Requests

If you have ideas for new features or improvements:

- Check if the feature has already been suggested in the issues
- Open a new issue with the label "enhancement"
- Clearly describe the feature and its potential benefits

Thank you to all the contributors who help improve this project!

## 🙏 Acknowledgments

- [CrewAI](https://github.com/joaomdmoura/crewai) for providing the agent orchestration framework
- [Replicate](https://replicate.com/) for the powerful AI image generation capabilities
- [Dynamic Mockups](https://app.dynamicmockups.com/) for the mockup generation API
- [OpenAI](https://openai.com/) for the language models that power our agents
- All the open-source libraries that make this project possible
- Everyone who has contributed to the development and improvement of this project

---

<p align="center">Made with ❤️ for Etsy creators</p>
