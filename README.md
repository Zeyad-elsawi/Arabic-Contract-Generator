Arabic Contract Generator using RAG and Gemini
This project is a web-based application built with Streamlit that automatically generates Arabic legal contracts. It leverages a Retrieval-Augmented Generation (RAG) pipeline, combining a local knowledge base of contract templates with the powerful generative capabilities of Google's Gemini Pro model to produce customized, contextually-aware legal documents.

📜 Table of Contents
Features

How It Works: The Technical Workflow

Theoretical Concepts

Retrieval-Augmented Generation (RAG)

Embeddings and Vector Stores

Project Structure

Setup and Installation

Usage

Dependencies

✨ Features
Dynamic Contract Generation: Create customized Arabic contracts based on user-provided details.

Template-Based: Utilizes a library of pre-written Arabic contract templates (.docx files) to ensure legal accuracy and relevance.

Intuitive Web UI: A simple, user-friendly interface built with Streamlit for easy input of contract details.

Powered by Gemini: Leverages Google's Gemini Large Language Model for coherent and professional text generation.

Downloadable Output: Generated contracts can be easily downloaded as text files.

Categorized Contracts: Supports various contract types, including sales, leases, construction, and more.

🔧 How It Works: The Technical Workflow
The application follows a sophisticated process to transform user inputs and document templates into a finished contract. This process is known as Retrieval-Augmented Generation (RAG).

Template Loading: The application first identifies the category of contract the user has selected (e.g., "Lease Contracts"). It then loads the relevant .docx template files from the local ./نماذج عقود/مصري - Copy directory using LangChain's UnstructuredWordDocumentLoader.

Text Chunking: Legal documents can be lengthy. To process them efficiently, the loaded text is broken down into smaller, semantically meaningful chunks using the RecursiveCharacterTextSplitter. This step is crucial for the embedding and retrieval process.

Embedding Generation: Each text chunk is converted into a numerical vector representation using a sentence-transformer model (all-MiniLM-L6-v2) via Hugging Face Embeddings. These vectors, or "embeddings," capture the semantic meaning of the text, allowing for comparisons based on context rather than just keywords.

Vector Indexing: The generated embeddings are stored and indexed in a FAISS (Facebook AI Similarity Search) vector store. This creates a searchable, in-memory database where we can quickly find text chunks that are semantically similar to a given query.

User Input: The Streamlit interface collects all the necessary details for the contract, such as the names of the parties, dates, financial values, and special terms.

Context Retrieval: When the user clicks "Generate Contract," the application performs a similarity search on the FAISS vector store. It looks for the document chunks that are most relevant to the selected contract type.

Prompt Augmentation: The retrieved text chunks are combined with the user's input to create a detailed, context-rich prompt. This "augments" the prompt with specific examples and phrasing from the original templates.

Contract Generation: This final, augmented prompt is sent to the Google Gemini Pro API. The LLM uses the provided context and user details to generate a complete, well-structured Arabic contract that is both customized and grounded in the provided legal templates.

🧠 Theoretical Concepts
Retrieval-Augmented Generation (RAG)
RAG is an advanced AI architecture that enhances the capabilities of Large Language Models (LLMs) by connecting them to external knowledge bases. Instead of relying solely on its pre-trained data, an LLM using RAG can pull in relevant, real-time information to answer questions or complete tasks.

In this project, RAG prevents the LLM from "hallucinating" or inventing legal clauses by forcing it to base its generation on the actual content retrieved from the trusted .docx templates.

Embeddings and Vector Stores
Embeddings are the cornerstone of modern NLP. They are dense vector representations of text where words and sentences with similar meanings are located close to each other in the vector space. This allows the algorithm to understand context and relevance in a way that simple keyword matching cannot.

A Vector Store (like FAISS) is a specialized database designed to store these embeddings and perform incredibly fast similarity searches. When we want to find the most relevant document chunks, we embed our query and ask the vector store to return the vectors (and their corresponding text) that are "closest" to our query vector.

📁 Project Structure
.
├── نماذج عقود/مصري - Copy/
│   ├── عقد بيع شقة.docx
│   ├── عقد إيجار.docx
│   └── ... (and other .docx templates)
├── app.py                  # Main Streamlit application script
├── requirements.txt        # List of Python dependencies
└── README.md               # This file
🚀 Setup and Installation
Follow these steps to run the project locally.

1. Clone the Repository

Bash

git clone <your-repository-url>
cd <repository-folder>
2. Create a Python Virtual Environment
It's highly recommended to use a virtual environment to manage project dependencies.

Bash

python -m venv venv
source venv/bin/activate   # On Windows, use `venv\Scripts\activate`
3. Install Dependencies
Install all the required Python libraries from the requirements.txt file.

Bash

pip install -r requirements.txt
4. Get a Gemini API Key

Go to the Google AI for Developers website and generate an API key.

Important: The provided code hardcodes the API key. This is not secure. It is strongly recommended to use an environment variable instead.

Set the environment variable in your terminal:

Bash

export GOOGLE_API_KEY="YOUR_API_KEY_HERE"  # On Linux/macOS
set GOOGLE_API_KEY="YOUR_API_KEY_HERE"    # On Windows
Then, modify the Python script to read the key from the environment:

Python

# In app.py
import os
gemini_api_key = os.getenv("GOOGLE_API_KEY")
5. Run the Streamlit App

Bash

streamlit run app.py
Open your web browser and navigate to the local URL provided by Streamlit (usually http://localhost:8501).

🖥️ Usage
Launch the application.

If you haven't set an environment variable, enter your Gemini API Key in the sidebar.

From the dropdown menu, select the main category of the contract you wish to generate (e.g., "عقود الإيجار" - Lease Contracts).

Fill in the details for both parties, dates, jurisdiction, and any other relevant terms in the form.

Click the "إنشاء العقد" (Generate Contract) button.

The application will process your request and display the generated contract in a text box.

You can review the text and click the "تحميل العقد" (Download Contract) button to save it as a .txt file.

📦 Dependencies
The project relies on the following major libraries:

streamlit: For creating the web application interface.

langchain-community: For document loading, text splitting, and vector store integration.

google-generativeai: The official Python SDK for the Gemini API.

sentence-transformers: For generating text embeddings.

faiss-cpu: For the vector store and similarity search functionality.

unstructured & python-docx: For parsing and reading .docx files.
