@echo off
setlocal
rem === Publica FanRank: tests -> commit -> push. Reutilizable (doble clic). ===
cd /d "C:\Users\anton\OneDrive\Escritorio\todo\CHAT GPT\Bot\PROYECTO MADRE\TEST_SUGERENCIAS\fanrank"
echo === PUBLICAR FANRANK %date% %time% === > publicar_log.txt
findstr /x "publicar_log.txt" .git\info\exclude >nul 2>&1 || echo publicar_log.txt>> .git\info\exclude

rem Lock huerfano de un proceso git muerto: quitarlo (esta noche solo publica este script)
if exist .git\index.lock (
  echo AVISO: habia .git\index.lock huerfano - eliminado >> publicar_log.txt
  del /f .git\index.lock >> publicar_log.txt 2>&1
)

echo [1/4] Tests...
python tests\test_fanrank.py >> publicar_log.txt 2>&1
if errorlevel 1 (
  echo TESTS ROJOS - NO SE PUBLICA >> publicar_log.txt
  echo TESTS ROJOS - NO SE PUBLICA. Mira publicar_log.txt
  pause
  exit /b 1
)

echo [2/4] Commit...
git add -A >> publicar_log.txt 2>&1
if errorlevel 1 (
  echo GIT ADD FALLO >> publicar_log.txt
  echo GIT ADD FALLO. Mira publicar_log.txt
  pause
  exit /b 1
)
git commit -m "feat(v17+v18+v19): famous directory, zero empty profiles, usability round, idea duel (Tony 16-jul)" >> publicar_log.txt 2>&1

echo [3/4] Verificando que no queda nada sin commitear...
git diff-index --quiet HEAD -- >> publicar_log.txt 2>&1
if errorlevel 1 (
  echo QUEDAN CAMBIOS SIN COMMITEAR - FALLO REAL >> publicar_log.txt
  echo COMMIT INCOMPLETO. Mira publicar_log.txt
  pause
  exit /b 1
)

echo [4/4] Push...
git push origin master >> publicar_log.txt 2>&1
if errorlevel 1 (
  echo PUSH FALLO >> publicar_log.txt
  echo PUSH FALLO. Mira publicar_log.txt
  pause
  exit /b 1
)
git log --oneline -1 >> publicar_log.txt 2>&1
echo PUBLICADO OK >> publicar_log.txt
echo PUBLICADO OK - esta ventana se cierra sola
timeout /t 8 >nul
exit /b 0
