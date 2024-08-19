# How to Contribute?

## Developpment
If you want to contribute to the project by improving said action, you will need to do the following setup:

- Create a new brach from dev or fork the repository
- Install the Python language of a [version][github-runners] supported by the GitHub runner `ubuntu:latest` image.
- Install Python dependencies for the part of the project you want to work on (each module has it's own `requirements.txt`) with `pip -r path/to/requirement.txt`
- You can test your action by running the `Test Action` workflow which you can customize by pointing it to your development branch
- When done, open a `pull request` towards the `dev` branch of the project

[github-runners]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md

## Code overview

The code of the project is highly commented as to express the extension of each module, so we recommend you go through it on your time. Here is a simple overview of the modules present and their roles

### Modules

- `action.yml` - The github action workflow itself
- `src/extraction` - The feature extraction script that is used as a first step of the action
  - `db` - Cache database and ORM configuration
  - `extract.py` - Main script
  - `features` - The Implementation of DB synchronization and feature extraction
- `src/analysis` - The analysis script implementing the ML model and the second step of the action
  - `analyze.py` - Main script
  - `analyzer.py` - Interface layer for the ML model, to simplify its usage
- `src/training_data` - Similar to extraction script, but tailored to generate training data to retrain the ML model
