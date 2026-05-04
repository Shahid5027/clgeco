# QR Attendance System

## Overview

A Flask-based web application that enables teachers to generate time-sensitive QR codes for student attendance tracking. The system provides separate interfaces for teachers (QR code generation, attendance reports) and students (QR code scanning, attendance marking). It uses CSV files for data persistence and implements real-time QR code validation with automatic expiration.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask**: Chosen for its simplicity and ease of setup for small-scale applications
- **Session-based authentication**: Uses Flask sessions for user state management without complex authentication systems
- **Template-based rendering**: Jinja2 templates with Bootstrap for responsive UI

### Data Storage
- **CSV-based persistence**: Simple file-based storage using CSV files for users and attendance records
- **In-memory session management**: Active QR sessions stored in global variables for real-time validation
- **No database dependency**: Eliminates need for database setup, making deployment simpler

### Authentication System
- **Role-based access**: Separate login flows for teachers and students
- **Hardcoded teacher credentials**: Demo-friendly approach with configurable credentials
- **Student registration**: Self-service registration using roll number suffixes

### QR Code Management
- **Time-sensitive QR codes**: QR codes expire after 5 seconds to prevent misuse
- **UUID-based session tokens**: Each QR code contains a unique session identifier
- **Real-time validation**: Server-side validation ensures QR codes are scanned within the valid time window

### Class Schedule Integration
- **Fixed schedule**: Predefined 7-hour class schedule with specific time slots
- **Time-based access control**: QR generation and scanning only available during active class hours
- **Automatic hour detection**: System automatically determines current class hour based on system time

### Frontend Architecture
- **Bootstrap 5**: Responsive design framework for mobile-friendly interface
- **Vanilla JavaScript**: Custom countdown timers and QR code management
- **Real-time updates**: JavaScript polling for QR code status and countdown display

## External Dependencies

### Python Libraries
- **Flask**: Web framework for routing and templating
- **pandas**: Data manipulation for CSV operations and attendance reporting
- **qrcode**: QR code generation with PIL/Pillow for image creation
- **uuid**: Unique session identifier generation

### Frontend Dependencies
- **Bootstrap 5.1.3**: CSS framework loaded via CDN
- **Base64 encoding**: In-browser QR code image display

### File System Dependencies
- **CSV files**: users.csv and attendance.csv for data persistence
- **Static assets**: CSS and JavaScript files served directly
- **Environment variables**: Session secret configuration

### Key Design Decisions
- **CSV over database**: Chosen for simplicity and portability, avoiding database setup complexity
- **Short QR validity**: 5-second expiration prevents screenshot sharing and ensures real-time attendance
- **Roll number-based authentication**: Simple student identification without password complexity
- **Time-based class detection**: Automatic scheduling reduces manual intervention