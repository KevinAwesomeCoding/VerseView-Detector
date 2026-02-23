      # Windows upload
      - name: Upload Windows artifact
        uses: actions/upload-artifact@v4
        with:
          name: VerseView-Detector-Windows
          path: "dist/VerseView Detector.exe"   # ← quoted

      # Mac DMG creation
      - name: Package as DMG
        run: |
          brew install create-dmg
          create-dmg \
            --volname "VerseView Detector" \
            --window-size 600 400 \
            --icon-size 120 \
            --app-drop-link 450 185 \
            "dist/VerseView Detector.dmg" \
            "dist/VerseView Detector.app"

      # Mac upload
      - name: Upload Mac artifact
        uses: actions/upload-artifact@v4
        with:
          name: VerseView-Detector-Mac
          path: "dist/VerseView Detector.dmg"   # ← quoted

      # Release job
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          tag_name: build-${{ steps.sha.outputs.short }}
          name: VerseView Detector Build ${{ steps.sha.outputs.short }}
          body: |
            Automated build from commit `${{ github.sha }}`

            **Download for your platform below:**
            - `VerseView Detector.exe` → Windows
            - `VerseView Detector.dmg` → Mac
          files: |
            "dist/VerseView Detector.exe"
            "dist/VerseView Detector.dmg"
          draft: false
          prerelease: false
