@echo off
cd /d "C:\Users\sowilo.in1\Documents\Spine\render-deployment"
git remote remove origin
git remote add origin https://github.com/aryaman-iyer/spine-attendance-1.git
git push -u origin main
pause
