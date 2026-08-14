# Project Handle

## Application

**Project name:** Lib InfoBot / PU Maubin Digital Library

**Manus project handle:** `DJYDm5GKWxaJLQreDFtnDj`

## Purpose

This handle identifies the continuing project context used for design and implementation continuity. It helps associate future work with the same Lib InfoBot project and its shared files/instructions.

## Security Note

The project handle is only an identifier. It is **not**:

- an OpenAI API key;
- a MySQL password;
- a Flask secret key;
- a user login credential; or
- a value that should be placed in `.env`, JavaScript, templates, or database tables.

Runtime configuration remains in the local `.env` file. The real `.env` file must not be committed or included in a distributable ZIP.

## Current Architecture

The application remains a Flask + MySQL system. Existing authentication/authorization, Book Search, Book Information, TF-IDF + Cosine Similarity recommendations, PDF upload/read/download, AI services, and LibInfoBot UI are separate from this identifier and are not changed by this document.
