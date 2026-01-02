---

# Sky-Bridge Siege [Architect Update]

A fast-paced 3D hybrid of an **FPS (First-Person Shooter)** and a **Tactical Tetris-style Puzzle**. Defend your wall against waves of enemies while managing a rising tower of blocks that can collapse if built poorly.

## 🎮 Game Overview

In **Sky-Bridge Siege**, you aren't just fighting enemies; you are fighting physics. An AI "Architect" drops blocks into a summoning zone behind your defensive wall. If the tower grows too high, the game is over.

### Key Mechanics:

* **The Architect:** 95% of the time, the AI provides perfect pieces to build flat floors. 5% of the time, it introduces "Chaos" blocks to mess up your tower's stability.
* **Structural Collapse:** Uneven floors (floors with gaps) cannot support heavy weight. If you build two floors on top of an uneven one, the base layer will explode and the tower will drop.
* **Slice Ability:** Switch to "Slice Mode" to identify perfectly filled (solid) floors. Click them to vaporize the layer into particles and lower your tower height.
* **Combat:** Use your pulse rifle, grenades, or a tactical Nuke to clear enemies scaling your walls.

---

## 🛠 Controls

| Key | Action |
| --- | --- |
| **W, A, S, D** | Move Player |
| **Mouse / Arrows** | Aim / Look |
| **Space / Left Click** | Fire Pulse Rifle |
| **Q** | Throw Grenade (Arcing Projectile) |
| **E** | **Toggle Slice Mode** (Interact with Tower) |
| **O** | Trigger Tactical Nuke (Requires 20 Killstreak) |
| **Right Click** | Toggle FPS / TPS Camera |
| **R** | Restart Game |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.x
* PyOpenGL
* PyOpenGL_accelerate (Optional, for better performance)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/sky-bridge-siege.git

```


2. Install dependencies:
```bash
pip install PyOpenGL PyOpenGL_accelerate

```


3. Run the game:
```bash
python main.py

```



---

## 🏗 Project Architecture

The project is built on the **OpenGL Fixed Function Pipeline** using **GLUT** for window and input management.

* **Coordinate System:** The world uses a 3D Cartesian system where `+Z` is Up.
* **Ray-Casting:** Slice Mode uses a custom ray-plane intersection algorithm to determine which tower layer the player is looking at.
* **Collision Engine:** Real-time AABB (Axis-Aligned Bounding Box) checks for projectiles and enemies, combined with grid-occupancy checks for the Tetris tower.

---