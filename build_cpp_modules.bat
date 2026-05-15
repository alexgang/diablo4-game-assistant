@echo off
setlocal

echo ============================================
echo  Game Assistant - OCR and TTS C++ Build
echo ============================================
echo.

set "CMAKE=C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "OV_DIR=C:\Program Files (x86)\Intel\openvino"
set "PROJECT_DIR=C:\AIPC\game assistant\demo test"

if not exist "%CMAKE%" (
    echo ERROR: CMake not found at expected path
    echo Searching for cmake...
    where cmake 2>nul && set "CMAKE=cmake" || (
        echo ERROR: CMake not found. Please install or add to PATH.
        pause
        exit /b 1
    )
)

if not exist "%OV_DIR%\runtime" (
    echo ERROR: OpenVINO not found at %OV_DIR%
    pause
    exit /b 1
)

echo [1/5] Setting up OpenVINO environment...
call "%OV_DIR%\setupvars.bat"

echo.
echo [2/5] Checking PaddleOCR_OpenVINO_CPP source...
cd /d "%PROJECT_DIR%"
if not exist "PaddleOCR_OpenVINO_CPP" (
    echo PaddleOCR_OpenVINO_CPP not found. Attempting git clone...
    git clone https://github.com/openvino-dev-samples/PaddleOCR_OpenVINO_CPP.git 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: Cannot clone from GitHub. Network unavailable.
        echo Please manually download from:
        echo   https://github.com/openvino-dev-samples/PaddleOCR_OpenVINO_CPP/archive/refs/heads/main.zip
        echo Extract to: %PROJECT_DIR%\PaddleOCR_OpenVINO_CPP
        echo Then re-run this script.
        echo.
        echo Skipping PaddleOCR build. Press any key to continue to MeloTTS...
        pause >nul
        goto :melotts
    )
) else (
    echo PaddleOCR_OpenVINO_CPP source found.
)

echo.
echo [3/5] Building PaddleOCR_OpenVINO_CPP...
cd /d "%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP"
if not exist "build" mkdir build
cd build
"%CMAKE%" -G "Visual Studio 17 2022" -A x64 -DOpenVINO_DIR="%OV_DIR%\runtime\cmake" ..
if errorlevel 1 (
    echo ERROR: CMake configure failed for PaddleOCR
    pause
    exit /b 1
)
"%CMAKE%" --build . --config Release
if errorlevel 1 (
    echo ERROR: Build failed for PaddleOCR
    pause
    exit /b 1
)
echo PaddleOCR_OpenVINO_CPP built successfully!
echo.
echo Testing PaddleOCR with sample image...
set "PATH=%OV_DIR%\runtime\bin\intel64\Release;%OV_DIR%\runtime\3rdparty\tbb\bin;C:\opencv\build\x64\vc16\bin;%PATH%"
if exist "%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\build\Release\reader.exe" (
    if exist "%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\models\ch_PP-OCRv4_det_infer\inference.pdmodel" (
        "%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\build\Release\reader.exe" --type=ocr --input="%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\data\ocr.jpg" --det_model_dir="%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\models\ch_PP-OCRv4_det_infer\inference.pdmodel" --cls_model_dir="%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\models\ch_ppocr_mobile_v2.0_cls_infer\inference.pdmodel" --rec_model_dir="%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\models\ch_PP-OCRv4_rec_infer\inference.pdmodel" --label_dir="%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\data\ppocr_keys_v1.txt"
    ) else (
        echo WARNING: PaddleOCR models not found. Download from:
        echo   https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar
        echo   https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar
        echo   https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar
        echo   Extract to: %PROJECT_DIR%\PaddleOCR_OpenVINO_CPP-main\models\
    )
)

:melotts
echo.
echo [4/5] Checking MeloTTS.cpp source...
cd /d "%PROJECT_DIR%"
if not exist "MeloTTS.cpp" (
    echo MeloTTS.cpp not found. Attempting git clone...
    git lfs install 2>nul
    git clone https://github.com/apinge/MeloTTS.cpp.git --branch multilang-develop 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: Cannot clone from GitHub. Network unavailable.
        echo Please manually download from:
        echo   https://github.com/apinge/MeloTTS.cpp/archive/refs/heads/multilang-develop.zip
        echo Extract to: %PROJECT_DIR%\MeloTTS.cpp
        echo Then re-run this script.
        echo.
        echo NOTE: MeloTTS requires model files in ov_models/ directory.
        echo Download from: https://huggingface.co/apinge/MeloTTS.cpp
        echo.
        pause
        exit /b 1
    )
) else (
    echo MeloTTS.cpp source found.
)

echo.
echo [5/5] Building MeloTTS.cpp...
cd /d "%PROJECT_DIR%\MeloTTS.cpp"
if not exist "build" mkdir build
cd build
"%CMAKE%" -G "Visual Studio 17 2022" -A x64 -DOpenVINO_DIR="%OV_DIR%\runtime\cmake" ..
if errorlevel 1 (
    echo ERROR: CMake configure failed for MeloTTS
    pause
    exit /b 1
)
"%CMAKE%" --build . --config Release
if errorlevel 1 (
    echo ERROR: Build failed for MeloTTS
    pause
    exit /b 1
)
echo MeloTTS.cpp built successfully!

echo.
echo ============================================
echo  Build Complete!
echo ============================================
echo.
if exist "%PROJECT_DIR%\PaddleOCR_OpenVINO_CPP\build\Release\reader.exe" (
    echo PaddleOCR: OK
) else (
    echo PaddleOCR: NOT BUILT - source code needed
)
if exist "%PROJECT_DIR%\MeloTTS.cpp\build\Release\meloTTS_ov.exe" (
    echo MeloTTS:   OK
) else (
    echo MeloTTS:   NOT BUILT - source code needed
)
echo.
pause
