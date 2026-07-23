# Git Setup Commands — img_vid_aud_check Fork

All commands used to set up the forked repository and push to the `optimize-ml-models` branch.

---

## 1. Clone Your Fork

```bash
git clone https://github.com/mrviperoffical-ux/img_vid_aud_check.git
```

---

## 2. Add Upstream (Original Owner's Repo)

```bash
git remote add upstream https://github.com/ashishjaiswal222/img_vid_aud_check.git
```

---

## 3. Verify Remotes

```bash
git remote -v
```

Expected output:
```
origin    https://github.com/mrviperoffical-ux/img_vid_aud_check.git (fetch)
origin    https://github.com/mrviperoffical-ux/img_vid_aud_check.git (push)
upstream  https://github.com/ashishjaiswal222/img_vid_aud_check.git (fetch)
upstream  https://github.com/ashishjaiswal222/img_vid_aud_check.git (push)
```

---

## 4. Fetch All Branches from Upstream

```bash
git fetch upstream
```

---

## 5. List All Branches (local + remote)

```bash
git branch -a
```

---

## 6. Checkout the `optimize-ml-models` Branch from Upstream

```bash
git checkout -b optimize-ml-models upstream/optimize-ml-models
```

---

## 7. Set Git Identity (Global)

```bash
git config --global user.name "myviper"
git config --global user.email "mrviperoffical@gmail.com"
```

---

## 8. Set Authenticated Remote URL (with PAT Token)

```bash
git remote set-url origin https://<YOUR_USERNAME>:<YOUR_PAT_TOKEN>@github.com/mrviperoffical-ux/img_vid_aud_check.git
```

> Replace `<YOUR_USERNAME>` with `mrviperoffical-ux` and `<YOUR_PAT_TOKEN>` with your GitHub fine-grained personal access token.
> Token must have **Contents: Read and write** permission for `img_vid_aud_check` repo.

---

## 9. Push Branch to Your Fork

```bash
git push origin optimize-ml-models
```

---

## Day-to-Day Workflow (After Setup)

```bash
# 1. Make your code changes

# 2. Stage all changes
git add .

# 3. Commit with a message
git commit -m "your commit message here"

# 4. Push to your fork
git push origin optimize-ml-models
```

---

## Sync Your Fork with Upstream (When Original Repo Gets Updates)

```bash
git fetch upstream
git checkout optimize-ml-models
git merge upstream/optimize-ml-models
git push origin optimize-ml-models
```

---

## Create a Pull Request

After pushing your changes, open a PR by visiting:
```
https://github.com/mrviperoffical-ux/img_vid_aud_check/pull/new/optimize-ml-models
```

This will let you request `ashishjaiswal222` to merge your changes into the original repo.

---

## Remotes Summary

| Remote   | URL                                                          | Purpose                        |
|----------|--------------------------------------------------------------|--------------------------------|
| origin   | https://github.com/mrviperoffical-ux/img_vid_aud_check.git  | Your fork (push changes here)  |
| upstream | https://github.com/ashishjaiswal222/img_vid_aud_check.git   | Original repo (pull updates)   |
