# PowerShell script to create GitHub repository and push code

Write-Host "Creating GitHub repository..." -ForegroundColor Green

# Create the repository using GitHub API (requires authentication)
$repoName = "spine-attendance"
$description = "Automated attendance system for Spine HR using Selenium"

Write-Host ""
Write-Host "Please follow these steps:" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/new" -ForegroundColor Cyan
Write-Host "2. Repository name: $repoName" -ForegroundColor Cyan
Write-Host "3. Keep it Private" -ForegroundColor Cyan
Write-Host "4. DON'T add README or .gitignore" -ForegroundColor Cyan
Write-Host "5. Click 'Create repository'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Enter when you've created the repository..."
Read-Host

# Open GitHub in browser
Start-Process "https://github.com/new"

Write-Host ""
Write-Host "After creating the repo, what is your GitHub username?" -ForegroundColor Yellow
$username = Read-Host "GitHub username"

Write-Host ""
Write-Host "Pushing code to GitHub..." -ForegroundColor Green

# Add remote and push
git remote remove origin 2>$null
git remote add origin "https://github.com/$username/$repoName.git"
git branch -M main
git push -u origin main

Write-Host ""
Write-Host "Done! Your code is now on GitHub at:" -ForegroundColor Green
Write-Host "https://github.com/$username/$repoName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next step: Deploy on Render" -ForegroundColor Yellow
Write-Host "1. Go to: https://dashboard.render.com/" -ForegroundColor Cyan
Write-Host "2. Sign in with GitHub" -ForegroundColor Cyan
Write-Host "3. New + > Web Service" -ForegroundColor Cyan
Write-Host "4. Connect the $repoName repository" -ForegroundColor Cyan
Write-Host "5. Click 'Create Web Service'" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
