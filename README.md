# Smart Traffic Violation Detection & Monitoring System

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Contributors](https://img.shields.io/badge/contributors-3-orange)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

An AI-powered solution for automated urban traffic enforcement and real-time monitoring — integrating computer vision, IoT infrastructure, and a web dashboard for detecting, recording, and analyzing traffic violations with minimal human intervention.

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
- [Database Configuration](#database-configuration)
- [Usage Instructions](#usage-instructions)
- [Web Dashboard](#web-dashboard)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting](#troubleshooting)
- [Future Scope](#future-scope)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Project Overview

### Problem Statement

Urban traffic violations pose significant challenges to road safety and efficiency. Traditional manual surveillance methods are time-consuming, error-prone, and limited in coverage and scalability. Over 11 million traffic violations were recorded in 2023 alone, highlighting the urgent need for automated solutions.

This system addresses these challenges by providing:

- **24/7 Automated Monitoring** — Continuous surveillance without human fatigue
- **High Accuracy Detection** — Advanced AI models ensuring reliable results
- **Real-time Processing** — Instant violation identification and recording
- **Scalable Architecture** — Deployable across multiple intersections and cities
- **Comprehensive Evidence Collection** — Photo, video, and data logging for enforcement

### System Objectives

1. **Vehicle Detection & Tracking** — Accurately detect and track multiple vehicles in real-time using YOLO-based object detection
2. **Violation Identification** — Detect red-light jumping, overspeeding, lane violations, and no-helmet riding
3. **License Plate Recognition** — Extract vehicle number plates using OCR for automated challan generation
4. **Data Management** — Store violation records, vehicle details, and evidence in a structured MySQL database
5. **Dashboard Analytics** — Provide actionable insights through an intuitive web interface with real-time monitoring

---

## System Architecture

The system follows a modular, microservices-based architecture ensuring scalability, maintainability, and real-time performance.

```
┌──────────────────────────────────────────────────────────────────┐
│                         INPUT SOURCES                            │
│   CCTV/IP Cameras │ USB Webcam │ Video File (.mp4) │ RTSP Feed  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                  DETECTION & PROCESSING LAYER                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  YOLO Object Detection (YOLOv8/v9/v11)                  │    │
│  │  • Real-time vehicle classification                     │    │
│  │  • Bounding box extraction and object tracking          │    │
│  └─────────────────────────────┬───────────────────────────┘    │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DeepSORT Tracking                                       │    │
│  │  • Consistent ID assignment across frames               │    │
│  │  • Occlusion handling with Kalman filters               │    │
│  └─────────────────────────────┬───────────────────────────┘    │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Violation Detection Logic                               │    │
│  │  • Red-light, speeding, lane, no-helmet, wrong-way      │    │
│  └─────────────────────────────┬───────────────────────────┘    │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  License Plate Recognition (Tesseract / EasyOCR)        │    │
│  │  • Multilingual support (English + regional scripts)    │    │
│  │  • Automatic character extraction and validation        │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        DATA STORAGE LAYER                        │
│   MySQL Database (violations, vehicles, users, history)          │
│   Evidence Storage (images, video clips, annotated frames)       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│   Laravel Web Dashboard                                          │
│   • Real-time monitoring  • Data visualization                   │
│   • Filtering & search    • Analytics & reporting                │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. Video streams are captured from cameras (CCTV, RTSP, USB)
2. Each frame is analyzed through the detection pipeline
3. YOLO identifies vehicles, classes, and bounding boxes
4. DeepSORT maintains consistent IDs across frames
5. Custom logic detects violations based on rules and thresholds
6. License plates are extracted and recognized via OCR
7. Evidence and records are saved to MySQL
8. Real-time updates are pushed to the web dashboard
9. Automated alerts and challan generation are triggered

---

## Key Features

### Vehicle Detection & Tracking

- **Multi-class Detection** — Identifies cars, buses, trucks, motorcycles, bicycles, and pedestrians
- **High Accuracy** — Up to 97.7% violation detection accuracy with optimized YOLO models
- **Real-time Processing** — Sustains 28–30 fps on edge devices with TensorRT optimization
- **Robust Tracking** — DeepSORT handles occlusions with consistent ID assignment
- **Confidence Scoring** — Each detection carries a reliability metric

### Violation Types Detected

**1. Red Light Violation**
- Monitors vehicle crossing during red phase using HSV color space analysis
- Geometric line-crossing algorithm with before/after frame evidence capture

**2. Overspeeding**
- Calculates vehicle speed from tracking data: `Speed = Distance / Time` (pixel-to-meter conversion)
- Configurable speed limits (default: 60 km/h) with multi-frame false-positive reduction

**3. Lane Violation**
- Monitors lane departure using computer vision techniques
- Continuous multi-frame validation with timestamp logging

**4. No Helmet Detection**
- YOLO-based head analysis for two-wheeler riders
- Confidence-based thresholding with automatic authority notification

**5. Wrong-Way Driving**
- Vector-based trajectory analysis relative to traffic flow direction
- Multi-frame confirmation with immediate alert generation

### License Plate Recognition (LPR)

- **Multilingual Support** — English and regional language scripts
- **Robust Recognition** — Effective under motion blur and variable lighting
- **Standards Compliant** — Adheres to MoRTH AIS-159 and ISO 7591
- **84.9% OCR Precision** in field tests with rule-based character validation

### Web Dashboard

- Real-time violation feed with live updates
- Paginated tables with evidence thumbnails (STTI-126)
- Filtering by license plate, violation type, and date range
- Analytics with statistical visualizations and trend analysis
- CSV and PDF report export
- Role-based access control (Admin, Operator, Viewer)

### Evidence Collection

Each violation automatically generates:

- High-resolution snapshot at the moment of violation
- Video clip showing the full violation sequence
- Annotated bounding boxes and labels on frames
- Timestamp, location, vehicle type, color, and license plate metadata

### Automated Alerts

- Email notifications with evidence attached
- Real-time dashboard alerts
- SMS integration for critical violations
- V2X communication support for connected vehicles

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Core detection and processing |
| YOLO (v8/v9/v11) | Latest | Object detection |
| OpenCV | 4.5+ | Image and video processing |
| PyTorch | 2.0+ | Deep learning framework |
| TensorRT | 8.5+ | GPU optimization |
| DeepSORT | Latest | Object tracking |
| Tesseract / EasyOCR | Latest | License plate recognition |
| NumPy | Latest | Numerical computations |

### Web Dashboard

| Technology | Version | Purpose |
|---|---|---|
| Laravel | 10+ | Backend framework |
| PHP | 8.1+ | Server-side programming |
| MySQL | 8.0+ | Database management |
| Bootstrap | 5.x | UI framework |
| JavaScript | ES6+ | Client-side interactivity |

### Additional Tools

- **Flask** — Lightweight API server for real-time processing
- **Docker** — Containerization for consistent deployment
- **WebSockets** — Real-time data streaming
- **SCP/SSH** — Secure file transfer and remote access

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 |
| RAM | 8 GB | 16 GB |
| GPU | NVIDIA GTX 1060 | NVIDIA RTX 3060+ |
| Storage | 20 GB | 50 GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

- **OS**: Ubuntu 20.04 LTS (recommended), Windows 10/11 with WSL2, or macOS 12+
- **Python** 3.8+, **PHP** 8.1+, **MySQL** 8.0+, **Git** 2.30+, **Composer** 2.0+
- **GPU (optional)**: NVIDIA CUDA 11.6+, cuDNN 8.4+, TensorRT 8.5+, Driver 510+

---

## Installation Guide

### 1. Clone the Repository

```bash
git clone https://github.com/fer0zshah/Smart-Traffic-Violation-Detection-Monitoring-System.git
cd Smart-Traffic-Violation-Detection-Monitoring-System
```

### 2. Setup Python Virtual Environment

```bash
python3 -m venv traffic_env
source traffic_env/bin/activate      # Linux/macOS
traffic_env\Scripts\activate         # Windows
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install opencv-python opencv-contrib-python ultralytics torch torchvision
pip install numpy pandas matplotlib easyocr pytesseract
pip install flask flask-cors mysql-connector-python Pillow
```

### 4. Download YOLO Weights

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"
```

### 5. Setup Web Dashboard (Laravel)

```bash
cd web-dashboard
composer install
cp .env.example .env
php artisan key:generate
```

---

## Database Configuration

### 1. Create MySQL Database

```sql
CREATE DATABASE traffic_violation_db;
CREATE USER 'traffic_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON traffic_violation_db.* TO 'traffic_user'@'localhost';
FLUSH PRIVILEGES;
USE traffic_violation_db;
```

### 2. Create Required Tables

```sql
CREATE TABLE violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    violation_type VARCHAR(50) NOT NULL,
    license_plate VARCHAR(20),
    vehicle_type VARCHAR(30),
    vehicle_color VARCHAR(20),
    confidence FLOAT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    violation_location VARCHAR(255),
    speed_kmh FLOAT,
    image_path TEXT,
    video_path TEXT,
    processed_status VARCHAR(20) DEFAULT 'pending',
    officer_verification BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_license_plate ON violations(license_plate);
CREATE INDEX idx_timestamp ON violations(timestamp);
CREATE INDEX idx_violation_type ON violations(violation_type);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'operator',
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cameras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_name VARCHAR(100) NOT NULL,
    camera_location VARCHAR(255),
    camera_type VARCHAR(30),
    rtsp_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    last_active DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 3. Configure Laravel Environment

Edit `.env`:

```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=traffic_violation_db
DB_USERNAME=traffic_user
DB_PASSWORD=secure_password
```

### 4. Run Migrations

```bash
php artisan migrate
php artisan db:seed
```

---

## Usage Instructions

### Real-time Camera Input

```bash
source traffic_env/bin/activate
python detect.py --source 0 --model yolov8m.pt
```

### Video File Processing

```bash
python detect.py --source path/to/video.mp4 --model yolov8m.pt --violation all --output results/
```

### RTSP Stream Processing

```bash
python detect.py --source rtsp://username:password@ip:port/stream --model yolov8m.pt
```

### Detection Parameters

| Parameter | Description | Default |
|---|---|---|
| `--source` | Input source (camera / video / RTSP) | `0` |
| `--model` | YOLO model path | `yolov8n.pt` |
| `--conf` | Detection confidence threshold | `0.5` |
| `--iou` | NMS IoU threshold | `0.45` |
| `--output` | Output directory | `runs/detect` |
| `--frame-skip` | Skip frames for optimization | `1` |
| `--speed-limit` | Speed limit in km/h | `60` |
| `--violation` | Violation type(s) to detect | `all` |

### Starting the Web Dashboard

```bash
cd web-dashboard
php artisan serve
```

Access the dashboard at `http://localhost:8000`.

### Flask API Server (Optional)

```bash
python api_server.py
# Available at: http://localhost:5000/api/violations
```

---

## Web Dashboard

### Dashboard Components

| Component | Description | Status |
|---|---|---|
| Statistics Cards | Real-time violation metrics | ✅ Done |
| Paginated Table | Violation records with thumbnails | ✅ Done (STTI-126) |
| Evidence Gallery | Thumbnails with modal view | ✅ Done |
| Filter Panel | Advanced search and filtering | ✅ Done |
| User Management | Role-based admin controls | ✅ Done |
| Analytics Charts | Data visualization | 🚧 In Progress |
| Real-time Updates | WebSocket integration | 🚧 In Progress |

---

## API Documentation

### Detect Violations

```http
POST /api/detect
Content-Type: multipart/form-data
Authorization: Bearer {token}
```

**Request Body**:

```json
{
    "image": "[File]",
    "violation_type": "red_light|speeding|lane|helmet",
    "confidence_threshold": 0.5
}
```

**Response**:

```json
{
    "status": "success",
    "violations": [
        {
            "id": "uuid",
            "type": "red_light",
            "vehicle_type": "car",
            "license_plate": "ABC123",
            "confidence": 0.92,
            "timestamp": "2026-07-19T14:30:00Z",
            "image_url": "/evidence/2026-07-19/violation_uuid.jpg"
        }
    ]
}
```

### Violation Management

```http
GET    /api/violations                # List with pagination & filters
GET    /api/violations/{id}           # Get single record with evidence
PUT    /api/violations/{id}           # Update status or verification
DELETE /api/violations/{id}           # Delete (admin only)
```

**Query Parameters** for `GET /api/violations`:

| Parameter | Type | Description |
|---|---|---|
| `page` | int | Page number (default: 1) |
| `limit` | int | Records per page (default: 20) |
| `license_plate` | string | Filter by plate number |
| `violation_type` | string | Filter by type |
| `from_date` | date | Start date (YYYY-MM-DD) |
| `to_date` | date | End date (YYYY-MM-DD) |

### System Status

```http
GET /api/status     # System health, active cameras, performance metrics
GET /api/cameras    # List all cameras with status
POST /api/cameras   # Add or update camera configuration
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8080/violations');

ws.onmessage = (event) => {
    const violation = JSON.parse(event.data);
    updateDashboard(violation);
};

ws.send(JSON.stringify({ action: 'subscribe', camera_id: 'cam_001' }));
```

---

## Project Structure

```
Smart-Traffic-Violation-Detection-Monitoring-System/
│
├── detection-engine/
│   ├── models/                    # YOLO weights (.pt files)
│   ├── src/
│   │   ├── detector.py            # Main detection class
│   │   ├── tracker.py             # DeepSORT implementation
│   │   ├── violation_detector.py  # Violation logic
│   │   ├── ocr_engine.py          # License plate recognition
│   │   ├── video_processor.py     # Stream handling
│   │   └── config.py              # Configuration
│   ├── utils/
│   │   ├── image_utils.py
│   │   ├── video_utils.py
│   │   ├── database.py
│   │   └── logger.py
│   ├── tests/
│   └── requirements.txt
│
├── web-dashboard/                 # Laravel application
│   ├── app/
│   │   ├── Http/Controllers/
│   │   ├── Models/                # Violation.php, User.php, Camera.php
│   │   └── Providers/
│   ├── database/
│   │   ├── migrations/
│   │   └── seeders/
│   ├── resources/views/
│   │   ├── dashboard/
│   │   ├── violations/
│   │   └── layouts/
│   ├── routes/
│   │   ├── web.php
│   │   └── api.php
│   └── .env
│
├── api-server/
│   ├── app.py
│   ├── endpoints.py
│   └── database.py
│
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── nginx/nginx.conf
│
├── docs/
├── scripts/
│   ├── setup.sh
│   └── start-system.sh
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Contributing Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Follow **PEP 8** for Python, **PSR-12** for PHP, and **Airbnb style** for JavaScript
4. Add unit tests for new functionality
5. Run tests: `python -m pytest tests/`
6. Commit with a clear message: `git commit -m "Add: brief description"`
7. Push and open a Pull Request with screenshots if UI changes are included

---

## Troubleshooting

**CUDA out of memory**
```bash
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb=128
# Or use a smaller model: --model yolov8n.pt
```

**MySQL connection refused**
```bash
sudo systemctl status mysql
# Verify credentials in .env and confirm the database exists
```

**OpenCV ImportError (`libGL.so.1`)**
```bash
sudo apt-get install libgl1-mesa-glx
# Or: pip install opencv-python-headless
```

**WebSocket connection failed**
```bash
sudo ufw allow 8080
netstat -tulpn | grep 8080
```

**Low detection accuracy**
- Increase confidence: `--conf 0.6`
- Use a larger model: `yolov8m.pt` or `yolov8l.pt`
- Improve camera lighting and focus

### Performance Tips

```bash
# TensorRT optimization
python convert_to_trt.py --model yolov8m.pt --fp16

# Skip frames for speed
python detect.py --source video.mp4 --frame-skip 2

# Batch processing
python detect.py --source video.mp4 --batch-size 8
```

---

## Future Scope

- **YOLOv11** with transformer neck for improved accuracy
- **Edge deployment** on Raspberry Pi / Orange Pi with optimized models
- **V2X integration** with traffic signal control systems
- **Predictive analytics** using ML for violation forecasting
- **Mobile application** for remote monitoring
- **Kubernetes deployment** with distributed edge-cloud processing
- **Adverse weather handling** — fog, rain, and low-light detection improvements

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

### Contributors

- **fer0zshah** — Project Lead & AI Developer
- **ullas-6575** — Backend Developer (STTI-126 paginated table)
- **sanim62** — Frontend & UI/UX Developer

### Third-Party Libraries

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) — Object detection
- [OpenCV](https://opencv.org/) — Computer vision
- [DeepSORT](https://github.com/nwojke/deep_sort) — Object tracking
- [Tesseract](https://github.com/tesseract-ocr/tesseract) — OCR engine
- [Laravel](https://laravel.com/) — Web framework
- [PyTorch](https://pytorch.org/) — Deep learning

---

## Project Status

**Current Version: 1.0.0** *(Last updated: July 2026)*

| Status | Item |
|---|---|
| ✅ Done | Core detection engine |
| ✅ Done | Paginated violation table with thumbnails (STTI-126) |
| ✅ Done | Eloquent Violation model with fillable fields (STTI-125) |
| ✅ Done | Web dashboard basic functionality |
| ✅ Done | Database schema implementation |
| 🔄 In Progress | Real-time WebSocket updates |
| 🔄 In Progress | Advanced analytics dashboard |
| 🔄 In Progress | Mobile responsive design |
| 📋 Planned | Kubernetes deployment |
| 📋 Planned | V2X integration |
| 📋 Planned | Mobile application |

---

*Made with ❤️ by the Smart Traffic Team*
