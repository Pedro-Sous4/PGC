# SDN Network Management System

A comprehensive Software-Defined Networking (SDN) management system for university networks with real-time monitoring, security threat detection, and intelligent traffic management.

## Features

### 1. Network Topology Discovery and Visualization
- Real-time topology mapping using OpenFlow protocols
- Interactive network graph visualization
- Automatic device discovery and categorization
- Physical and logical topology views

### 2. Traffic Monitoring and Analysis
- Real-time traffic flow monitoring
- Bandwidth utilization analysis
- Application-level traffic classification
- Historical traffic data analytics

### 3. Security Threat Detection and Response
- Network traffic analysis for anomaly detection
- ML-based threat identification
- Automatic security policy enforcement
- Real-time alerting system

### 4. SDN Controller Integration
- OpenFlow 1.3+ support
- Multi-vendor controller compatibility
- Flow rule management
- Network device configuration

### 5. Web-Based Management Interface
- Real-time dashboard
- Interactive topology viewer
- Policy management interface
- Analytics and reporting

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   Analytics     │    │   Security      │
│   (Flask/JS)    │    │   Engine        │    │   Module        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    Core Management System                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Topology      │   Traffic       │     SDN Controller          │
│   Discovery     │   Monitoring    │     Integration             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     Network Infrastructure                       │
│    OpenFlow Switches ├─── Routers ────┬─── Firewalls ────┬─────│
│                        │              │                  │     │
│                   Access Points    Servers          End Devices │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/university-IT/sdn-network-manager
cd sdn-network-manager
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the system:
```bash
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your network settings
```

5. Initialize database:
```bash
python scripts/init_db.py
```

## Usage

### Starting the System
```bash
python main.py
```

### Web Interface
Access the management dashboard at: `http://localhost:8080`

### Configuration
Edit `config/config.yaml` to customize:
- Network settings
- Controller connections
- Security policies
- Monitoring parameters

## Components

### Core Modules

1. **Topology Discovery** (`src/modules/topology/`)
   - Device discovery using LLDP, CDP
   - Network topology mapping
   - Graph visualization

2. **Traffic Monitoring** (`src/modules/traffic/`)
   - Flow statistics collection
   - Bandwidth analysis
   - Traffic classification

3. **Security Module** (`src/modules/security/`)
   - Anomaly detection
   - Threat intelligence
   - Policy enforcement

4. **SDN Controller** (`src/modules/sdn_controller/`)
   - OpenFlow communication
   - Flow rule management
   - Device configuration

### Web Interface

- **Dashboard**: Real-time network overview
- **Topology**: Interactive network visualization
- **Analytics**: Traffic and performance analysis
- **Security**: Threat monitoring and response
- **Policies**: Network rule management

## API Documentation

### REST API Endpoints

- `GET /api/topology` - Get current network topology
- `GET /api/traffic/stats` - Get traffic statistics
- `GET /api/security/threats` - Get security threats
- `POST /api/policies` - Create network policy
- `GET /api/devices` - List network devices

### WebSocket Events

- `traffic_update` - Real-time traffic data
- `topology_change` - Network topology updates
- `security_alert` - Security threat notifications

## Development

### Project Structure
```
sdn_network_manager/
├── src/
│   ├── core/              # Core system components
│   ├── modules/           # Feature modules
│   ├── web/              # Web interface
│   └── utils/            # Utility functions
├── config/               # Configuration files
├── tests/                # Test suites
├── docs/                 # Documentation
└── scripts/              # Deployment scripts
```

### Running Tests
```bash
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact:
- IT Support: it-support@university.edu
- Documentation: https://university-IT.github.io/sdn-docs