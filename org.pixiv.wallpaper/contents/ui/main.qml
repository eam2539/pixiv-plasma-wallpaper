/*
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtCore
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import QtQuick.Window
import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as Plasma5Support

WallpaperItem {
    id: root

    property string visibleImage: root.configuration.CurrentImage
    property string statusText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Loading Pixiv Wallpaper...")
    property string cacheImagesDir: StandardPaths.writableLocation(StandardPaths.HomeLocation) + "/.cache/pixiv-plasma-wallpaper/images"
    property string helperScript: String(StandardPaths.writableLocation(StandardPaths.HomeLocation)).replace(/^file:\/\//, "") + "/.local/share/plasma/wallpapers/org.pixiv.wallpaper/contents/code/pixiv_wallpaper.py"
    property var failedImages: ({})
    contextualActions: [
        PlasmaCore.Action {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Rotate Now")
            icon.name: "view-refresh"
            onTriggered: root.rotateNow()
        },
        PlasmaCore.Action {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Fetch Images Now")
            icon.name: "folder-download"
            onTriggered: Qt.openUrlExternally("pixiv-plasma-wallpaper://fetch-now")
        },
        PlasmaCore.Action {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Choose Local Image")
            icon.name: "document-open"
            onTriggered: localImageDialog.open()
        },
        PlasmaCore.Action {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Open Current Image")
            icon.name: "document-open"
            enabled: root.visibleImage.length > 0
            onTriggered: Qt.openUrlExternally(root.pathToUrl(root.visibleImage))
        },
        PlasmaCore.Action {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Open Pixiv Page")
            icon.name: "internet-services"
            visible: root.currentPixivIllustId().length > 0
            enabled: root.currentPixivIllustId().length > 0
            onTriggered: Qt.openUrlExternally("https://www.pixiv.net/artworks/" + root.currentPixivIllustId())
        }
    ]

    function screenWidth() {
        return Math.max(1, Math.round(root.width * Screen.devicePixelRatio));
    }

    function screenHeight() {
        return Math.max(1, Math.round(root.height * Screen.devicePixelRatio));
    }

    function cachedImages() {
        var value = root.configuration.CachedImages;
        return root.uniquePaths(root.valueToList(value));
    }

    function valueToList(value) {
        var images = [];
        if (value instanceof Array) {
            images = value;
        } else {
            images = String(value || "").split(/[\n,]/);
        }
        return images.map(function(path) { return String(path || "").trim(); });
    }

    function uniquePaths(images) {
        var seen = {};
        return images.filter(function(path) {
            path = String(path || "");
            if (path.length === 0 || seen[path] || root.failedImages[path]) {
                return false;
            }
            seen[path] = true;
            return true;
        });
    }

    function isImagePath(path) {
        return /\.(jpe?g|png|webp|bmp)$/i.test(path);
    }

    function currentPixivIllustId() {
        if (!root.visibleImage || root.cachedImages().indexOf(root.visibleImage) < 0) {
            return "";
        }
        var name = root.visibleImage.split("/").pop();
        var match = /^(\d+)_/.exec(name);
        return match ? match[1] : "";
    }

    function localImages() {
        var paths = root.valueToList(root.configuration.LocalImageCache);
        var configuredPaths = root.valueToList(root.configuration.LocalImagePaths);
        for (var p = 0; p < configuredPaths.length; p++) {
            if (root.isImagePath(configuredPaths[p])) {
                paths.push(configuredPaths[p]);
            }
        }
        var images = [];
        for (var i = 0; i < paths.length; i++) {
            var path = paths[i];
            if (path.length === 0) {
                continue;
            }
            if (root.isImagePath(path)) {
                images.push(path);
            }
        }
        return root.uniquePaths(images);
    }

    function localImageCacheKey() {
        return String(root.configuration.LocalImagePaths || "");
    }

    function syncLocalImageCache() {
        if (!root.configuration.IncludeLocalImages) {
            return;
        }
        syncLocalImageCacheTimer.restart();
    }

    Timer {
        id: syncLocalImageCacheTimer
        interval: 1000
        repeat: false
        onTriggered: executable.connectSource("/usr/bin/python3 " + root.helperScript + " sync-local-cache")
    }

    function hasLocalFolderPaths() {
        var paths = root.valueToList(root.configuration.LocalImagePaths);
        for (var i = 0; i < paths.length; i++) {
            if (paths[i].length > 0 && !root.isImagePath(paths[i])) {
                return true;
            }
        }
        return false;
    }

    function combinedImages() {
        return root.uniquePaths(root.cachedImages().concat(root.localImages()));
    }

    function ratioImages() {
        if (!root.configuration.IncludeLocalImages) {
            return root.cachedImages();
        }
        var local = root.localImages();
        var cached = root.cachedImages();
        if (local.length === 0) {
            return cached;
        }
        if (cached.length === 0) {
            return local;
        }
        var ratio = Math.max(0, Math.min(100, Number(root.configuration.LocalImageRatio || 50)));
        return Math.random() * 100 < ratio ? local : cached;
    }

    function rotationImages() {
        return root.ratioImages();
    }

    function removeCachedImage(path) {
        if (!path || path.length === 0) {
            return [];
        }
        root.failedImages[path] = true;
        var images = root.cachedImages().filter(function(image) { return image !== path; });
        var localImages = root.valueToList(root.configuration.LocalImagePaths).filter(function(image) { return image !== path; });
        root.configuration.CachedImages = images;
        root.configuration.LocalImagePaths = localImages.join("\n");
        if (root.configuration.CurrentImage === path) {
            root.configuration.CurrentImage = "";
            root.configuration.CurrentIndex = -1;
        }
        root.configuration.writeConfig();
        return images;
    }

    function rotateNow() {
        console.log("Pixiv Wallpaper: rotateNow triggered");
        var images = [];
        try {
            images = root.rotationImages();
        } catch (error) {
            console.log("Pixiv Wallpaper: cached image parse failed", error);
        }
        console.log("Pixiv Wallpaper: cached image count", images.length, "current image", root.visibleImage);
        if (images.length === 0) {
            if (root.configuration.IncludeLocalImages && root.hasLocalFolderPaths()) {
                root.syncLocalImageCache();
            }
            root.statusText = i18nd("plasma_wallpaper_org.pixiv.wallpaper", "No wallpapers available yet.");
            console.log("Pixiv Wallpaper:", root.statusText);
            return;
        }

        var mode = String(root.configuration.RotationMode || "sequential");
        var currentIndex = images.indexOf(root.visibleImage);
        if (currentIndex < 0) {
            currentIndex = images.indexOf(root.configuration.CurrentImage);
        }
        var nextIndex = mode === "random" ? Math.floor(Math.random() * images.length) : (currentIndex + 1) % images.length;
        if (mode === "random" && images.length > 1 && images[nextIndex] === root.visibleImage) {
            nextIndex = (nextIndex + 1) % images.length;
        }
        var nextImage = images[nextIndex];
        root.configuration.CurrentImage = nextImage;
        root.configuration.CurrentIndex = nextIndex;
        root.configuration.LastRotate = Date.now().toString();
        root.configuration.writeConfig();
        root.statusText = i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Showing wallpaper.");
        root.setVisibleImage(nextImage);
        console.log("Pixiv Wallpaper: rotated to", nextImage);
    }

    function setVisibleImage(path) {
        root.visibleImage = path;
        wallpaperImage.source = "";
        if (!path || path.length === 0) {
            root.loading = false;
            return;
        }
        root.loading = true;
        wallpaperImage.sourceSize = Qt.size(root.screenWidth(), root.screenHeight());
        Qt.callLater(function() {
            if (root.visibleImage === path) {
                wallpaperImage.source = root.imageSource(path);
            }
        });
    }

    function imageSource(path) {
        if (!path || path.length === 0) {
            return "";
        }
        return root.pathToUrl(path);
    }

    function pathToUrl(path) {
        if (!path || path.length === 0) {
            return "";
        }
        return "file://" + path.split("/").map(function(part) { return encodeURIComponent(part); }).join("/");
    }

    function fileUrlToPath(url) {
        var text = String(url || "");
        if (text.indexOf("file://") === 0) {
            return decodeURIComponent(text.substring(7));
        }
        return text;
    }

    function chooseLocalImage(path) {
        if (!path || path.length === 0) {
            return;
        }
        var images = root.valueToList(root.configuration.LocalImagePaths);
        if (images.indexOf(path) < 0) {
            images.unshift(path);
        }
        root.configuration.LocalImagePaths = images.join("\n");
        root.configuration.CurrentImage = path;
        root.configuration.CurrentIndex = images.indexOf(path);
        root.configuration.LastRotate = Date.now().toString();
        root.configuration.writeConfig();
        root.statusText = i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Showing selected local image.");
        console.log("Pixiv Wallpaper:", root.statusText, path);
        root.setVisibleImage(path);
    }

    function cacheImagesUrl() {
        return root.pathToUrl(root.cacheImagesDir);
    }

    Plasma5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            executable.disconnectSource(source);
        }
    }

    function ensureHelperSetup() {
        executable.connectSource("/usr/bin/python3 " + root.helperScript + " setup");
    }

    Component.onCompleted: {
        root.loading = true;
        root.ensureHelperSetup();
        root.syncLocalImageCache();
        if (root.visibleImage.length > 0) {
            root.setVisibleImage(root.visibleImage);
        }
    }

    Connections {
        target: root.configuration
        function onLocalImagePathsChanged() {
            root.syncLocalImageCache();
        }
        function onIncludeLocalImagesChanged() {
            root.syncLocalImageCache();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.configuration.Color
    }

    Image {
        id: wallpaperImage
        anchors.fill: parent
        z: 1
        fillMode: root.configuration.FillMode
        asynchronous: true
        cache: false
        autoTransform: true
        smooth: true
        onStatusChanged: {
            if (status === Image.Ready) {
                root.loading = false;
                root.accentColorChanged();
            } else if (status === Image.Error) {
                var failedImage = root.visibleImage;
                console.log("Pixiv Wallpaper: image failed to load", failedImage);
                root.removeCachedImage(failedImage);
                root.statusText = i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Image failed to load, skipping.");
                console.log("Pixiv Wallpaper:", root.statusText);
                root.setVisibleImage("");
                Qt.callLater(root.rotateNow);
                root.accentColorChanged();
            }
        }
    }

    Timer {
        interval: 5000
        repeat: true
        running: true
        onTriggered: {
            if (root.visibleImage !== root.configuration.CurrentImage) {
                root.setVisibleImage(root.configuration.CurrentImage);
            }
        }
    }

    FileDialog {
        id: localImageDialog
        title: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Choose Local Image")
        currentFolder: root.cacheImagesUrl()
        nameFilters: [i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Image files (*.jpg *.jpeg *.png *.webp *.bmp)")]
        onAccepted: root.chooseLocalImage(root.fileUrlToPath(selectedFile))
    }

    QQC2.Label {
        anchors.centerIn: parent
        width: parent.width * 0.8
        visible: wallpaperImage.status !== Image.Ready
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: "white"
        text: root.statusText
        style: Text.Outline
        styleColor: "black"
    }
}
