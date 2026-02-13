.PHONY: build install clean macos linux windows help

# Автоопределение ОС
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	OS := macos
	BINARY := dist/claude-code-cli-hub.app
	ARCHIVE := dist/claude-code-cli-hub-macos-x86_64.dmg
else ifeq ($(UNAME_S),Linux)
	OS := linux
	BINARY := dist/claude-code-cli-hub
	ARCHIVE := dist/claude-code-cli-hub-linux-x86_64.tar.gz
else
	OS := windows
	BINARY := dist/claude-code-cli-hub.exe
	ARCHIVE := dist/claude-code-cli-hub-windows-x86_64.zip
endif

help:
	@echo "Доступные команды:"
	@echo "  make install  - установить зависимости для сборки"
	@echo "  make build    - собрать для текущей ОС ($(OS))"
	@echo "  make macos    - собрать для macOS"
	@echo "  make linux    - собрать для Linux"
	@echo "  make windows  - собрать для Windows"
	@echo "  make clean    - удалить папки build и dist"
	@echo "  make run      - запустить собранное приложение"

install:
	pip install -e ".[build]"

build: $(BINARY)
	@echo "Сборка завершена: $(BINARY)"

macos:
	@echo "Сборка для macOS..."
	pyinstaller claude-code-cli-hub.spec
	@echo "Создание DMG..."
	cd dist && hdiutil create -volname "Claude Code CLI Hub" \
		-srcfolder claude-code-cli-hub.app \
		-ov -format UDZO \
		claude-code-cli-hub-macos-x86_64.dmg || true
	@echo "Готово: dist/claude-code-cli-hub-macos-x86_64.dmg"

linux:
	@echo "Сборка для Linux..."
	pyinstaller claude-code-cli-hub.spec
	@echo "Создание архива..."
	cd dist && tar -czf claude-code-cli-hub-linux-x86_64.tar.gz claude-code-cli-hub
	@echo "Готово: dist/claude-code-cli-hub-linux-x86_64.tar.gz"

windows:
	@echo "Сборка для Windows..."
	pyinstaller claude-code-cli-hub.spec
	@echo "Создание архива..."
	cd dist && powershell Compress-Archive -Path claude-code-cli-hub.exe -DestinationPath claude-code-cli-hub-windows-x86_64.zip -Force
	@echo "Готово: dist/claude-code-cli-hub-windows-x86_64.zip"

dist/claude-code-cli-hub.app dist/claude-code-cli-hub dist/claude-code-cli-hub.exe: main.py claude-code-cli-hub.spec
	pyinstaller claude-code-cli-hub.spec

run:
ifeq ($(OS),macos)
	open dist/claude-code-cli-hub.app
else ifeq ($(OS),linux)
	./dist/claude-code-cli-hub
else
	./dist/claude-code-cli-hub.exe
endif

clean:
	rm -rf build dist *.spec.bak
