
# Apps for Video Scene Matching

## Part 1 – Dual Video Annotation Tool

This project is the first component of the *Apps for Video Scene Matching* system. It is designed to manually annotate time intervals from a control video while simultaneously comparing it with a reference video.

The application allows the user to watch two videos side by side and mark specific time ranges from the control video. These selected intervals are exported into a CSV file for further processing.

For instance, we used this to match the similar scenes and locations between a movie and its game version.

---

## Project Overview

The system consists of two video panels:

### Left Panel – Control Video

* Audio enabled
* Fully controllable (play, pause, forward, backward, seek)
* Used for marking time intervals

### Right Panel – Reference Video

* Audio disabled
* Looped playback
* Fully controllable (play, pause, forward, backward, seek)
* Used for visual comparison only

The purpose of this setup is to manually segment meaningful portions of the control video while visually comparing it to a reference video.

---

## How It Works

1. The application automatically searches the working directory for:

   * `control_*.mp4` (also supports `.mov`, `.avi`, `.mkv`)
   * `reference_*.mp4` (same supported formats)

2. The first matching files are loaded automatically:

   * Left → Control video
   * Right → Reference video

3. While watching the control video:

   * Press **X** to mark the start time
   * Press **C** to mark the end time

4. Each marked interval:

   * Is displayed in a scrollable on-screen list
   * Is written to a CSV file

---

## Output

The application generates (or appends to) a file named:

```
output.csv
```

Each row follows the format:

```
start_time,end_time
```

Time format:

```
HH:MM:SS
```

These intervals represent the selected time ranges from the control video.

---

## Controls

### Keyboard

* `X` → Mark start time
* `C` → Mark end time
* `ESC` → Exit application

### Mouse

* Play / Pause button
* Forward / Backward (30 seconds)
* Click progress bar to seek
* Scroll interval list using mouse wheel

---

## Technologies Used

* Python
* pygame
* ffpyplayer
* CSV file handling

---

## Purpose

This tool was developed to support manual scene segmentation and structured time-based annotation between two videos. The exported intervals can later be used for:

* Scene matching
* Frame synchronization
* Behavioral comparison
* Dataset preparation for further studies

---

## Part 2 – Interval Matching Interface

This is the second component of the *Apps for Video Scene Matching* system.

In the first application, both videos are processed separately as **control videos**, and meaningful time intervals are manually extracted from each one. As a result, two separate CSV files are generated:

* `film.csv` → Time intervals from the first video
* `game.csv` → Time intervals from the second video

This second application is designed to load those interval files, visualize them alongside the videos, and allow manual matching between corresponding scenes.

---

## Project Purpose

The goal of this module is to:

* Load two previously segmented videos
* Display their extracted time intervals
* Allow the user to visually inspect each interval
* Manually match related scenes between the two videos
* Store matched pairs in a structured CSV file

This enables structured scene alignment between two different video sources (e.g., film vs. game footage).

---

## How It Works

### 1. Interval Extraction (From Part 1)

Each video is first processed independently using the annotation tool.
This produces:

* `film.csv`
* `game.csv`

Each CSV contains:

```
start,end
```

in `HH:MM:SS` format.

---

### 2. Loading the Videos

The application automatically searches for:

* `control_*.mp4` → Left panel (Film)
* `reference_*.mp4` → Right panel (Game)

Supported formats: mp4, mov, avi, mkv

---

### 3. Interface Structure

The screen is divided into:

Left side:

* Two video panels (Film & Game)
* Each with playback controls (play, pause, skip, seek)

Right side:

* Two scrollable interval lists:

  * Film intervals
  * Game intervals

---

### 4. Matching Logic

* Clicking an interval automatically seeks the video to that start time.
* One interval from Film and one from Game can be selected.
* Press **X** to create a match.
* Press **C** to remove a selected match.

Matched intervals are:

* Highlighted in the interface
* Stored in `matches.csv`

---

## Output

The system generates:

```
matches.csv
```

Format:

```
film_start,film_end,game_start,game_end
```

This file represents the mapping between corresponding scenes in both videos.

---

## Technologies Used

* Python
* pygame
* ffpyplayer
* CSV file handling

---

## System Workflow Summary

1. Extract intervals independently from both videos (Part 1).
2. Load interval CSV files into this interface.
3. Visually inspect intervals.
4. Match corresponding scenes manually.
5. Export structured scene alignment data.

---

## Development Status

This project is still under active development.

The current implementation successfully demonstrates the core workflow of manual interval extraction and structured scene matching. However, the internal architecture—particularly in terms of object-oriented design—can be further improved. Certain components would benefit from refactoring to achieve better separation of concerns, cleaner class responsibilities, and improved maintainability.

Future improvements may include:

* Refactoring the codebase to strengthen OOP structure

* Modularizing video handling and matching logic

* Enhancing UI responsiveness and usability

* Adding synchronization and assisted matching features

* Optimizing performance for larger video datasets

This project represents an evolving system rather than a finalized product, and it serves as a foundation for further architectural refinement and feature expansion.

