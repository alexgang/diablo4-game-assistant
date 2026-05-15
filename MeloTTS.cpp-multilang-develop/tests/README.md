## Frequently Asked Questions (FAQ)


# How to enable test
When generate the solution, use 
```
cmake -B build -S . -DENABLE_TEST
```
# How build and run certain test
```
cmake --build build --target clean
cmake --build build --target test_bert --config Release
build\tests\Release\test_bert.exe
```

# Error	MSB3073	The command "setlocal
When building test
```
Error	MSB3073	The command "setlocal
"C:\Program Files\CMake\bin\cmake.exe" -D TEST_TARGET=test_bert -D TEST_EXECUTABLE==C:/repos/MeloTTS.cpp/build/tests/Release/test_bert.exe -D TEST_EXECUTOR= -D TEST_WORKING_DIR==C:/repos/MeloTTS.cpp/build/tests -D TEST_EXTRA_ARGS= -D TEST_PROPERTIES= -D TEST_PREFIX= -D TEST_SUFFIX= -D TEST_FILTER= -D NO_PRETTY_TYPES=FALSE -D NO_PRETTY_VALUES=FALSE -D TEST_LIST=test_bert_TESTS -D CTEST_FILE==C:/repos/MeloTTS.cpp/build/tests/test_bert[1]_tests.cmake -D TEST_DISCOVERY_TIMEOUT=5 -D TEST_XML_OUTPUT_DIR= -P "C:/Program Files/CMake/share/cmake-3.29/Modules/GoogleTestAddTests.cmake"
if %errorlevel% neq 0 goto :cmEnd
:cmEnd
endlocal & call :cmErrorLevel %errorlevel% & goto :cmDone
:cmErrorLevel
exit /b %1
:cmDone
if %errorlevel% neq 0 goto :VCEnd
:VCEnd" exited with code 1.	test_bert	C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Microsoft\VC\v170\Microsoft.CppCommon.targets	166		
```
Please Refer to https://stackoverflow.com/questions/50434096/cgal-building-install-sln-error-msb3073-the-command-setlocal
Run admin and cmd build the test

