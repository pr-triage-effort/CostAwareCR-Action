# PR Triage by Review Effort action

A GitHub Action to analyze the currently opened pull requests in a repository and reorder them by their merge probability and review priority.

## Overview

The action is part of a bigger project that aims to create tools which can help developers and maintainers to better allocate their energy and efforts towards tasks that will meaningfully help with their projects development. The present GitHub Action collects and analyses data about yhe currently opened pull requests and uses a specially trained machine learning algorithm that attempts prioritize pull requests according to their complexity, the merge probability and the amount of effort required for review.

The results of the analysis can then used to better direct the developer/maintainer time and effort towards analyzing pull requests that are more meaningful for the project or require the least effort reducing the seemingly endless list of potential contributions that have to be reviewed. The action is the back-end part of the tool and it is recommended to use the [Chrome Extension][chrome_extension] that was developed alongside in order to illustrate the result of the performed analysis in the GitHub Pull Request WebUI.

[chrome_extension]: https://chromewebstore.google.com/detail/pr-triage-effort-extensio/apcidpfpcfkiekneknhfabibgkjhlban?authuser=0&hl=en&pli=1

## Prerequisites

The GitHub Action is optimized with performance in mind where possible and requires the following to be used in your repository:

- A [GitHub token][token_doc] with API access
  - Can be the default `GITHUB_TOKEN` provided automatically at the start of each workflow run
  - Needs write action for the following scopes:
    - `contents`
    - `attestations`
    - `pull-requests`
  - Depending on repository size (open/closed PRs) may require a personal access token (PAT) to achieve adequate performance - see [following section](#data-caching)
- Cache space available in your repository
  - Is repository dependent (number of open/closed PRs)
  - Used by an SQLite database to accelerate future runs

[token_doc]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication

## Getting Started

Here is a minimal workflow configuration required to use the action in your repository

```yaml
name: Review Effort Analysis
on:
  pull-request:
    types: [opened, reopened, edited, synchronize, ready_for_review]
    branches:
      - main

concurrency:
  group: pr-analysis
  cancel-in-progress: false

jobs:
  analyze-prs:
    runs-on: ubuntu-latest
    steps:
    - name: PR Triage
      uses: pr-triage-effort/pr-triage-effort-action@v1
      with:
        github_token: ${{ secrets.ANALYSIS_TOKEN }}
```

This configuration contains a single job with one step that will run each time a pull request targeting our main branch is opened or updated. It uses only the provided `ANALYSIS_TOKEN` with necessary permissions (configured in your repository) but otherwise does not override any of the other action input arguments, which are all either optional or default targeting the the current repository by default. Let's walkthrough other parts of that configuration that you may adapt to your situation:

### Workflow trigger

The PR Triage by Review Effort action expects to be run in the context of a `pull_request` webhook event that targets the main branch. It ensures that the workflow is run each time a pull request is opened, reopened, its contents edited, a draft PR is marked as ready for review or changes have been committed to the base branch.

```yaml
on:
  pull-request:
    types: [opened, reopened, edited, synchronize, ready_for_review]
    # Targeted branch
    branches:
      - main
```

We also recommend to optionally set a scheduled run in a less busy time of the day to refresh the cached data that is used in the analysis to shorten the run-time during the day. You can do that by using the cron syntax:

```yaml
on:
  schedule:
    # The action will automatically run at midnight of each day
    - cron: "0 0 * * *" 
```

You can also trigger it manually by using a `workflow_dispatch` webhook directly in the GitHub Actions WebUI. This can help if you want to analyze a repository, but it is not possible (for some circumstances) to run this action inside said repository. This way you can create a workflow with this action and provide the `owner/repo` as input argument to scan that repository instead.

```yaml
on: 
  workflow_dispatch:
    inputs:
      repo:
        description: 'repo to analyze'
        required: false
```

### Permissions

When using the default `GITHUB_TOKEN` provided automatically at the start of each workflow run, you need to manually provide the required permissions in the workflow file. The PR Triage by Review Effort action needs write access for the `contents`,`attestations` and `pull-requests` scopes. If you are using a personal access token (PAT), you need to configure those permissions in the repository settings and add it to you secrets. See the [GitHub documentation][permission-scopes] for more info.

```yaml
permissions:
  contents: write
  attestations: write
  pull-requests: write
```

[permission-scopes]: https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes

### Concurrency

To avoid running multiple instance of the analysis job during a high influx of pull requests, it is recommended to use the concurrency configuration for that action that on any workflow trigger will queue only a single additional run of the workflow without disturbing the current run's execution.

```yaml
concurrency:
  group: pr-analysis
  cancel-in-progress: false
```

### Action Inputs

The action inputs ensures that the tool can run properly while accepting a small range of customizations that can be more appropriate for your use case.

```yaml
    steps:
    - name: PR Triage
      uses: pr-triage-effort/pr-triage-effort-action@v1
      with:
        # REQUIRED: The github access token that will be used by the action to interact with the GitHub API
        github_token: ${{ secrets.YOUR_TOKEN }}

        # OPTIONAL: The repository that you want to analyze. Defaults to the caller repository 
        repo: 'owner/repo'

        # OPTIONAL: Recreates the SQLite cache database. This ensures that all information is
        # up to date, but lengthens the run time considerably depending on project size. Recommended 
        # to use only in downtime hours. Defaults to FALSE
        cache_reset: 'false'

        # OPTIONAL: Amount in days that the cached data will be reused before it has to be recalculated
        # Defaults to 1 day, but can be adjusted according to your needs
        discard_data_after: '1'

        # OPTIONAL: The number of parallel processes used to speed-up SQLite cache generation when it
        # is not present or reset. This parameter should be adjusted carefully as it may compromise other
        # systems that rely on the same PAT token (rate-limiting) as it caches all open and closed PR info
        # to accelerate it's subsequent run time. More on that in the Data Caching section. Defaults to 2.
        prefill_processes: '2'
        
        # OPTIONAL: Path to the pre-existing SQLite database file in the repository (e.g., .github/scan/cache.db)'
        # Can be necessary if the project you are analyzing is too big. You can estimate the minimum runtime with the
        # formula in the 'Data Caching' section of the docs. If it's > 6h, must be used in order to install the action
        db_path: ''
```

## Data Caching

In order to optimize the performance of the GitHub Action in the day-to-day use where pull requests are constantly opened/closed/updated, on it's first run, the action creates an SQLite cache database and updates it to synchronize with the current state of all pull requests in the repository. This data is used in the calculation of metrics provided to the machine learning algorithm to perform the analysis. This initial fill consists of all opened and closed pull requests in the repository from which are derived current and historical metrics. Depending on the popularity of your project (number of open/closed PRs) this fill can take multiple hours. For this reason the use of `cache_reset` input is advised against in normal operation.

To accelerate the first fill, the action splits the data acquisition between multiple parallel processes, the number of which is defined by the `prefill_processes` input. Because it's an GitHub API intensive operation, this input's value should be chosen carefully depending on the allowed [rate-limits][rate-limits] of the `github_token` you provide to the action. For the initial fill, it is advised to, at least, provide a PAT with a 5,000 primary request limit. You can predict the estimated time of that fill with hte following formula:

`((open - draft) + closed) / hourly_request_limit = fill_time(h)`

Normally, you should leave the `prefill_processes` at it's default value, unless you have a 15,000 primary request limit token (Cloud Enterprise Account) or you are running this on a self-hosted GitHub Enterprise Server where you could loosen those limits. With the default 2 processes, the hourly 5,000 request cap is hit in around ~45min and no secondary rate-limits are triggered.

[rate-limits]: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api?apiVersion=2022-11-28

## Analyzing large projects

Some projects have too much of PRs to synchronize to the DB, and it may be impossible to install the action the normal way. Because the maximum job run-rime on GitHub hosted runners is limited to 6h, if your first run is unable to be finished by that time (use the `fill_time` formula) you may have to proceed in a more manual way to perform the first run, but after that it should work as always. The point of this procedure is to skip the DB synchronization step by providing an already pre-filled DB. Here is how to do it:

1. Clone the GitHub Action repository locally on any local machine
2. Create a `.env` file in the root directory of the project and configure minimally the following variables:
   - `GITHUB_TOKEN` - Your PAT for API authentication
   - `GITHUB_REPO` - The `{owner/repo}` pairing of the project you want to install the action on
3. If missing, install Python (min. version is 3.10)
4. Install the required dependencies with `pip install -r .\src\extraction\requirements.txt`
5. Run the feature extraction script: `python .\src\extraction\extract.py`
6. Wait until the execution finishes (can take some time depending on project size)
7. Grab the generated `cache.db` file and upload it somewhere in the project repo where you will be installing the action (ex. `.github/scan/cache.db`)
8. When running the action for the first time in you workflow, provide the path of the DB file to the `db_path` input of the action.

    ```yaml
    jobs:
    analyze-prs:
      runs-on: ubuntu-latest
      steps:
      - name: PR Triage
        uses: pr-triage-effort/pr-triage-effort-action@v1
        with:
          github_token: ${{ secrets.ANALYSIS_TOKEN }}
          db_path: '.github/scan/cache.db'
    ```

## Contributing

If you desire to offer help and contribute to the project, please read the developer [documentation](./docs/CONTRIBUTE.MD)

## License

The source code and documentation of project are released under the [MIT License](LICENSE)
