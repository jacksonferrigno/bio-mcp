# Bio-Inspired Innovation Engine - MCP Server

## 🚀 Overview

The Bio-Inspired Innovation Engine is a Python-based Model Context Protocol (MCP) server designed to augment Large Language Model (LLM) clients (such as Claude for Desktop) with powerful capabilities for research and ideation.
It specializes in finding and synthesizing bio-inspired solutions for user-defined problems.

This server connects to external search APIs (like Google Custom Search) to research problem domains and biological concepts, uses NLP for keyword extraction, stores findings in a PostgreSQL database for persistence and learning, and can generate structured Markdown reports.

The core idea is to leverage nature's ingenuity by identifying relevant biological systems, abstracting their principles, and translating them into innovative solutions for diverse challenges.

## ✨ MCP Tools

The server provides a suite of tools that enable an LLM client to:

* **Research User Problems:** Take a user's problem description, perform web searches to gather general context, extract key concepts, and identify relevant links.
* **Find Initial Bio-Inspired Concepts:** Based on the problem's keywords and summary, generate biologically-focused search queries to discover potential biological systems, principles, or themes for inspiration.
* **Get Bio-Concept Overviews:** For a specific biological concept identified, perform targeted web searches to retrieve and format a detailed overview.
* **Store & Retrieve Findings:**
    * Allow the client to store key-value pairs (e.g., research results, synthesized ideas) into a PostgreSQL database, using JSONB for flexible data storage.
    * Fetch specific findings by key or retrieve all stored findings to build and utilize a persistent knowledge base.
* **Generate Markdown Reports:** Research overview client will display for user and will be saved to the server's local filesystem.

## 🛠️ Technology Stack

* Python 3.11.9
* **Model Context Protocol (MCP)**: Using the `mcp[cli]` library with `FastMCP`.
* **Web Interaction**: `httpx` for asynchronous HTTP requests.
* **Keyword Extraction**: `yake` (Yet Another Keyword Extractor).
* **Database**: PostgreSQL.
* **PostgreSQL Adapter**: `psycopg2-binary`.
* **Environment Management**: `python-dotenv` for loading API keys and configurations.
* **Package Management**: `uv` (from Astral).
* **External APIs**: Google Custom Search JSON API.

## 📄 Example Reports
  * [Optimizing Irrigation Systems in Metropolitan Areas Through Bio-Inspired Approaches_report](./Optimizing%20Irrigation%20Systems%20in%20Metropolitan%20Areas%20Through%20Bio-Inspired%20Approaches_report.md)
  * [Optimizing Startup Team Workflow Using Biological Models_report](./Optimizing%20Startup%20Team%20Workflow%20Using%20Biological%20Models_report.md)

