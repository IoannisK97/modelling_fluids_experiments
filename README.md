
# Modelling Fluid Dynamics Experiments

This repository contains a Python-based fluid dynamics simulation built incrementally. Each file adds a new feature to the simulation, starting from a basic Navier-Stokes solver and incorporating temperature, external forces, obstacles, and turbulence.
Initially I followed the tutorial from here https://medium.com/@zakariatemouch/exploring-fluid-dynamics-using-python-a-numerical-approach-with-navier-stokes-equations-0a00ddae6822 and then I added features.
My goal for this short project was to experiment with python to model a such dynamics.

---

## Files Overview

| File Name                                       | Description                              |
|------------------------------------------------|------------------------------------------|
| modellingfluidinitial.py                       | Implements the basic Navier-Stokes solver for 2D fluid dynamics. |
| modellingfluidwithtemperature.py               | Extends the initial simulation with temperature advection and diffusion. |
| modellingfluidwithtemperatureandobstacle.py    | Introduces obstacles to the simulation. Velocity is set to zero in the obstacle region. |
| modellingfluidwithtemperatureandobstacleandexternalforce.py | Adds external forces that vary spatially and temporally. |
| modellingfluidwithtemperatureandobstacleandexternalforceandturbulance.py | Incorporates a turbulence model using the Smagorinsky constant. |

---

## Features

- Real-time visualization of the velocity field, vorticity (curl), and temperature.
- Coupled simulation of fluid flow and heat transfer.
- Customizable parameters (e.g., viscosity, grid size, and time step).
- Interactive exploration of fluid dynamics concepts.

---

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/<repository-name>.git
2. Install dependencies:
   ```bash
    pip install numpy scipy matplotlib cmasher tqdm
3. Run the desired script:
   ```bash
   python modellingfluidwithtemperatureandobstacleandexternalforceandturbulance.py



