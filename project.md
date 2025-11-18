# Simple PyKV | Project Documentation

Simple PyKV will be a lightweight Python-based key-value storage server designed to facilitate the saving and retrieval of project-specific data through a RESTful HTTP API.

## Project Overview
The goal of Simple PyKV is to provide an easy-to-setup and maintain solution for managing key-value pairs without the complexity of a full database system. It is intended for small to medium-sized projects that need a straightforward way to handle data storage.

## Feature requirements
- Must be accessible via a RESTful HTTP API.
- Have different storage namespaces for different projects so there can multiple projects using the same server without data collision.
- Support in-memory storage for fast access, with an option to persist data to disk.
- Minimal dependencies to ensure lightweight deployment.
- Simple and intuitive API design for ease of use.
- Ability to handle basic CRUD operations (Create, Read, Update, Delete) for key-value pairs.
- Must use API keys or tokens for basic authentication and access control of overall system and per project. 
- config.json file to manage server settings such as port number, persistence options (global or per project), and authentication settings.

## Questions to address
- How will data persistence be handled? Will it use flat files, SQLite, or another method?
- How will per-project configuration be managed?:
    - How will projects be created and deleted? - via API or config file, or both?
    - How will project-specific settings (like persistence options) be defined and stored? - in config file or via API?
- What authentication mechanism will be implemented to secure access to the API? And for per-project access control?
- How will error handling and logging be implemented to ensure reliability and ease of debugging?

## Next Steps
- Define the API endpoints and their specifications.
- Choose the data persistence method and design the storage architecture.
- Implement authentication and access control mechanisms.
- Develop a prototype to test core functionalities and gather feedback.