# Publishing Steps

Steps to publish the Insurance Claim Document Processor to GitHub and LinkedIn.

## 1. Create GitHub Repository

Go to: https://github.com/new

- Repository name: `insurance-claim-processor`
- Description: "AWS Bedrock-powered document processing for automated insurance claim extraction. Built for AIP-C01 certification study."
- Visibility: Public
- Do NOT initialize with README (we already have one)
- Click "Create repository"

## 2. Set Remote and Push

```bash
cd ~/shared/insurance-claim-processor
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/insurance-claim-processor.git
git branch -M main
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.

## 3. Verify Repository

- Visit `https://github.com/YOUR_GITHUB_USERNAME/insurance-claim-processor`
- Confirm the repo is set to Public (check the label next to the repo name)
- Confirm README.md renders correctly with the architecture diagram, model evolution table, and code examples
- Confirm .gitignore excluded __pycache__ and .pyc files (they should not appear in the repo)

## 4. Post on LinkedIn

**Recommended format: LinkedIn Post (not Article)**

Posts get more engagement than articles on LinkedIn. The blog post is under 3000 characters, which fits in a standard post. If it exceeds the character limit when you paste it, trim the "Technical Decisions" section slightly.

Steps:
1. Go to LinkedIn > Start a post
2. Copy the content from `BLOG_POST.md` (everything above the `---` separator)
3. Paste into the post editor
4. LinkedIn will strip markdown formatting -- that's fine, the content reads well as plain text
5. Add the GitHub link where it says `[link placeholder]`

## 5. Add GitHub Link

Replace `[link placeholder]` in the post with:
```
https://github.com/YOUR_GITHUB_USERNAME/insurance-claim-processor
```

## 6. Add Hashtags

At the bottom of the post, add:
```
#awsexamprep #AWS #AmazonBedrock #GenAI #CloudComputing #MachineLearning
```

## 7. Optional: Tag AWS Exam Prep Team

The assignment recommends tagging #awsexamprep for visibility with the AWS Exam Prep team. You can also:
- Tag @AWS Training and Certification in the post
- Mention it was a bonus assignment from the AWS Exam Prep course
- The team monitors the #awsexamprep hashtag for endorsement opportunities

## Checklist Before Publishing

- [ ] Repo is public
- [ ] README renders correctly
- [ ] No AWS account IDs visible in any file
- [ ] No internal references (meshclaw, a2z.com, etc.)
- [ ] Blog post reads naturally (not robotic)
- [ ] GitHub link is correct in the LinkedIn post
- [ ] Hashtags are included
