# Contributing guide

This is based on [Home Assistant's](https://github.com/home-assistant/home-assistant) contributing docs: [[1](https://home-assistant.io/developers/development_environment/)], [[2](https://home-assistant.io/developers/development_catching_up/)]

## Code standards

We stick to [PEP8](https://www.python.org/dev/peps/pep-0008/) with the one exception being the indentation.
We use **tabs for indentation**.

Please stick to this to keep the code clean, readable and consistent.

## How to contribute

### If doing this for the first time
1. Fork this repo using the Fork button.
2. **Clone your fork** on your computer.
     
   **NOTE:** If you already have a fork of the original AlexaPi repository, the name's gonna collide, so GitHub is gonna name it AlexaPi-1 ... I've renamed mine to AlexaPiNG, which is cool, since it's just my own repo. You can basically name it whatever you want to, but you have to change it in the following commands where appropriate (not everywhere though!).

    ```
    git clone https://github.com/YOUR_GITHUB_USERNAME/AlexaPi.git
    ```

3. Add the main repo as `upstream`.

    ```
    cd AlexaPi
    git remote add upstream https://github.com/alexa-pi/AlexaPi.git
    ```

### Every time
1. Be sure to always work with the current upstream master.

    ```
    # Run this from your feature branch
    git fetch upstream master  # to pull the latest changes into a local branch
    git rebase upstream/master # to put those changes into your feature branch before your changes
    ```
2. Create a **feature branch** for your changes. This is important - don't push to master!

    ```
    git checkout -b new-feature
    ```
    
    Also, do a special branch based on your **`master`** for **each feature** you want to implement - don't put multiple features into one branch - this is also very important!
    
    Do your work here and `commit` it.
    If there is an issue in the tracker that regards your commits, always reference it in the commit message.
    For example `git commit -m "docs: add referencing issues (#2)"`.
3. Push this new branch into your fork.

    ```
    git push origin new-feature
    ```
    
4. Open a pull request using GitHub.
5. Wait for the PR to be accepted / cooperate with the developers to achieve this.
6. Enjoy having helped bunch of other users enjoying your changes :-) Thank you!

## Notes

- If you're looking for an IDE to use, you can try [PyCharm](https://www.jetbrains.com/pycharm/) Community - @renekliment uses that too. It is free and like other JetBrains products it's awesome. Just don't forget to set it to use tabs instead of spaces. It's written in Java and therefore can be a bit problematic if you have very small amount of system memory (RAM). 
- After you're done with improving your PR by pushing more commits into the feature branch that still covers the one thing, your commits may be _squashed_ to keep the history clean in the main repo.
- If having any doubts, don't hesitate to contact us.

## For core developers

Let's stick to the rule that no one (not even core developers) pushes directly to the repo. Every time one wants to make a change - even a silly one, it has to go through the Pull Request mechanism and at least one other core developer (one with push access to the repo) has to do a code review and agree with it before pulling it into `dev` or `master`.

### 14-day PR review window rule

When there is an open PR with no blocking objections for at least 14 days, it can be merged without explicit approval of other team members.

It's perfectly understandable that people don't have time to devote to AlexaPi to review stuff and if people with write access merge something even without a proper review, it will bring more good than harm to the project (keeps the development running, makes the project better as only people who have proved themselves have write access).

An attempt to contact relevant team members has to be made (team mention for example). This rule is to account for people being busy, unavailable or unwilling rather than trying to sneak PRs through.

## If you want to check out someone else's branch (for example a Pull Request)

**Always make sure there is no malicious code there before running it!**

- If you want to check out a Pull Request from your existing directory:

    ```
    git fetch upstream pull/PULL_ID/head:PULL_ID
    git checkout PULL_ID
    ```
    Where `PULL_ID` is the actual Pull Request number.

- If you want a fresh directory to do that:
    ```
    git clone -b NEW_FEATURE_BRANCH https://github.com/PERSONS_GIT_USERNAME/PERSONS_REPO_NAME.git AlexaPi
    ```
    Where `PERSONS_REPO_NAME` is usually `AlexaPi`, but can also be `AlexaPi-1`, `AlexaPiNG`, or anything else.