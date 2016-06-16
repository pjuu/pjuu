# How to contribute

We would love for you to contribute to pjuu!
This should be as easy as possible but there are a few things to consider when contributing...
If you intend to submit a pull request we ask that the following guidelines for contributing be followed as best as possible to help with the process. 

## How to prepare

* You will need a [GitHub account](https://github.com/signup/free)
* If there isnt an open ticket for your issue and/or your enhancement already, you can [open one here](https://github.com/pjuu/pjuu/issues)
    * When its a bug, please include the steps to reproduce it with as much detail as possible
    * If you can; mention the earliest version that you know is affected. You may need to use the commit ID.
  * If you plan on submitting a large bug report, it may be a good idea to use a [gist](https://gist.github.com/) or some other paste
    service of your choosing. 
* Fork the repository on GitHub

## Making Changes

* In your forked repository, create a branch for your upcoming patch.
    * Create a branch, idealy based on master; `git branch
    yourbranch master` then checkout the new branch with `git
    checkout yourbranch`.  It would be advisable to avoid working directly on the master branch.
* Make your commits as logical units and ensure you describe them well.
* Check for unnecessary whitespace with `git diff --check` before committing.

* Where possible, submit tests to your patch / new feature so it can be tested easily.
* Assure nothing is broken by running all the tests.

## Submiting Changes

* Push your changes to the branch in your fork of the repository.
* When you are ready, open a pull request to the original repository and choose the original branch you want to patch.
* If not done in commit messages (which you really should do) please reference and update your issue with the code changes.
* Even if you have write access to the repository, Please do not directly push or merge pull-requests yourself. Let another team member review your pull request and approve it.

# Additional Resources

* [General GitHub documentation](https://help.github.com/)
* [GitHub pull request documentation](https://help.github.com/send-pull-requests/)



