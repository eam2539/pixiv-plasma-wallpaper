/*
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kquickcontrols as KQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: root
    twinFormLayouts: parentLayout

    property string cfg_RefreshToken
    property string cfg_Mode
    property string cfg_Theme
    property int cfg_RefreshMinutes
    property int cfg_RefreshSeconds
    property bool cfg_AutoFetch
    property int cfg_RotateMinutes
    property int cfg_RotateSeconds
    property bool cfg_AutoRotate
    property int cfg_MaxFetchCount
    property int cfg_FetchArtworkCount
    property string cfg_LocalImagePaths
    property string cfg_RotationMode
    property bool cfg_IncludeLocalImages
    property int cfg_MinBookmarks
    property int cfg_MinViews
    property string cfg_TagBlacklist
    property bool cfg_IncludeR18
    property bool cfg_IncludeAI
    property bool cfg_LandscapeOnly
    property int cfg_FitTolerance
    property int cfg_FillMode
    property alias cfg_Color: colorButton.color
    property bool cfg_NotifyEvents

    property int refreshHoursPart: 0
    property int refreshMinutesPart: 0
    property int refreshSecondsPart: 0
    property int rotateHoursPart: 0
    property int rotateMinutesPart: 0
    property int rotateSecondsPart: 0

    function normalizeSeconds(rawSeconds, rawMinutes, fallbackMinutes) {
        var seconds = Number(rawSeconds || 0);
        if (!isFinite(seconds) || seconds <= 0) {
            seconds = Number(rawMinutes || 0) * 60;
        }
        if (!isFinite(seconds) || seconds <= 0) {
            seconds = fallbackMinutes * 60;
        }
        return Math.max(1, Math.round(seconds));
    }

    function splitSeconds(totalSeconds) {
        var total = Math.max(0, Math.round(totalSeconds));
        var hours = Math.floor(total / 3600);
        var minutes = Math.floor((total % 3600) / 60);
        var seconds = total % 60;
        return {"hours": hours, "minutes": minutes, "seconds": seconds};
    }

    function syncRefreshPartsFromConfig() {
        var parts = splitSeconds(normalizeSeconds(cfg_RefreshSeconds, cfg_RefreshMinutes, 360));
        refreshHoursPart = parts.hours;
        refreshMinutesPart = parts.minutes;
        refreshSecondsPart = parts.seconds;
    }

    function syncRotatePartsFromConfig() {
        var parts = splitSeconds(normalizeSeconds(cfg_RotateSeconds, cfg_RotateMinutes, 30));
        rotateHoursPart = parts.hours;
        rotateMinutesPart = parts.minutes;
        rotateSecondsPart = parts.seconds;
    }

    function applyRefreshParts() {
        var total = Math.max(1, refreshHoursPart * 3600 + refreshMinutesPart * 60 + refreshSecondsPart);
        cfg_RefreshSeconds = total;
        cfg_RefreshMinutes = Math.max(1, Math.ceil(total / 60));
    }

    function applyRotateParts() {
        var total = Math.max(1, rotateHoursPart * 3600 + rotateMinutesPart * 60 + rotateSecondsPart);
        cfg_RotateSeconds = total;
        cfg_RotateMinutes = Math.max(1, Math.ceil(total / 60));
    }

    onCfg_RefreshSecondsChanged: syncRefreshPartsFromConfig()
    onCfg_RefreshMinutesChanged: syncRefreshPartsFromConfig()
    onCfg_RotateSecondsChanged: syncRotatePartsFromConfig()
    onCfg_RotateMinutesChanged: syncRotatePartsFromConfig()

    Component.onCompleted: {
        syncRefreshPartsFromConfig();
        syncRotatePartsFromConfig();
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Refresh token:")
        Layout.fillWidth: true

        QQC2.TextField {
            Layout.fillWidth: true
            text: cfg_RefreshToken
            echoMode: TextInput.PasswordEchoOnEdit
            placeholderText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Pixiv OAuth refresh_token")
            onTextChanged: cfg_RefreshToken = text
        }

        QQC2.Button {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Login")
            icon.name: "internet-services"
            onClicked: Qt.openUrlExternally("pixiv-plasma-wallpaper://login")
        }
    }

    QQC2.ComboBox {
        id: modeCombo
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Source:")
        textRole: "label"
        valueRole: "value"
        model: [
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Daily recommendations"), "value": "recommended" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Theme search"), "value": "search" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Daily ranking"), "value": "ranking" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Following"), "value": "follow" }
        ]
        onActivated: cfg_Mode = currentValue
        Component.onCompleted: {
            for (var i = 0; i < model.length; i++) {
                if (model[i].value === cfg_Mode) {
                    currentIndex = i;
                    break;
                }
            }
        }
    }

    QQC2.TextField {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Theme/tag:")
        Layout.fillWidth: true
        text: cfg_Theme
        placeholderText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Example: landscape, 初音ミク")
        onTextChanged: cfg_Theme = text
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Fetch every:")
        Layout.fillWidth: true
        enabled: cfg_AutoFetch

        QQC2.SpinBox {
            from: 0
            to: 999
            value: refreshHoursPart
            editable: true
            onValueModified: {
                refreshHoursPart = value;
                root.applyRefreshParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "h") }

        QQC2.SpinBox {
            from: 0
            to: 59
            value: refreshMinutesPart
            editable: true
            onValueModified: {
                refreshMinutesPart = value;
                root.applyRefreshParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "m") }

        QQC2.SpinBox {
            from: 0
            to: 59
            value: refreshSecondsPart
            editable: true
            onValueModified: {
                refreshSecondsPart = value;
                root.applyRefreshParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "s") }
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Auto fetch Pixiv images")
        checked: cfg_AutoFetch
        onToggled: cfg_AutoFetch = checked
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Rotate every:")
        Layout.fillWidth: true
        enabled: cfg_AutoRotate

        QQC2.SpinBox {
            from: 0
            to: 999
            value: rotateHoursPart
            editable: true
            onValueModified: {
                rotateHoursPart = value;
                root.applyRotateParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "h") }

        QQC2.SpinBox {
            from: 0
            to: 59
            value: rotateMinutesPart
            editable: true
            onValueModified: {
                rotateMinutesPart = value;
                root.applyRotateParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "m") }

        QQC2.SpinBox {
            from: 0
            to: 59
            value: rotateSecondsPart
            editable: true
            onValueModified: {
                rotateSecondsPart = value;
                root.applyRotateParts();
            }
        }

        QQC2.Label { text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "s") }
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Auto rotate wallpapers")
        checked: cfg_AutoRotate
        onToggled: cfg_AutoRotate = checked
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Max images per fetch:")
        from: 1
        to: 200
        value: cfg_MaxFetchCount
        onValueModified: cfg_MaxFetchCount = value
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Artwork count per fetch:")
        from: 1
        to: 50
        value: cfg_FetchArtworkCount
        onValueModified: cfg_FetchArtworkCount = value
    }

    QQC2.TextArea {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Local image paths:")
        Layout.fillWidth: true
        implicitHeight: Kirigami.Units.gridUnit * 5
        text: cfg_LocalImagePaths
        enabled: cfg_IncludeLocalImages
        placeholderText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "One file or folder per line")
        wrapMode: TextEdit.WrapAnywhere
        onTextChanged: cfg_LocalImagePaths = text
    }

    QQC2.ComboBox {
        id: rotationModeCombo
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Sort order:")
        textRole: "label"
        valueRole: "value"
        model: [
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Modified time (newest first)"), "value": "mtime_desc" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Modified time (oldest first)"), "value": "mtime_asc" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Random (non-repeating cycle)"), "value": "random" }
        ]
        onActivated: cfg_RotationMode = currentValue
        Component.onCompleted: {
            if (cfg_RotationMode === "sequential") {
                cfg_RotationMode = "mtime_desc";
            }
            for (var i = 0; i < model.length; i++) {
                if (model[i].value === cfg_RotationMode) {
                    currentIndex = i;
                    break;
                }
            }
        }
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Include local images")
        checked: cfg_IncludeLocalImages
        onToggled: cfg_IncludeLocalImages = checked
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Min bookmarks:")
        from: 0
        to: 1000000
        value: cfg_MinBookmarks
        onValueModified: cfg_MinBookmarks = value
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Min views:")
        from: 0
        to: 100000000
        value: cfg_MinViews
        onValueModified: cfg_MinViews = value
    }

    QQC2.TextArea {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Tag blacklist:")
        Layout.fillWidth: true
        implicitHeight: Kirigami.Units.gridUnit * 4
        text: cfg_TagBlacklist
        placeholderText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "One tag per line, or comma separated")
        wrapMode: TextEdit.WrapAnywhere
        onTextChanged: cfg_TagBlacklist = text
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Prefer landscape images")
        checked: cfg_LandscapeOnly
        onToggled: cfg_LandscapeOnly = checked
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Allow R-18 images")
        checked: cfg_IncludeR18
        onToggled: cfg_IncludeR18 = checked
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Allow AI generated images")
        checked: cfg_IncludeAI
        onToggled: cfg_IncludeAI = checked
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Aspect tolerance:")
        from: 5
        to: 100
        value: cfg_FitTolerance
        textFromValue: function(value) { return i18nd("plasma_wallpaper_org.pixiv.wallpaper", "%1%", value); }
        valueFromText: function(text) { return parseInt(text) || value; }
        onValueModified: cfg_FitTolerance = value
    }

    QQC2.ComboBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Positioning:")
        textRole: "label"
        valueRole: "fillMode"
        model: [
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Scaled and cropped"), "fillMode": Image.PreserveAspectCrop },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Scaled, keep proportions"), "fillMode": Image.PreserveAspectFit },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Stretched"), "fillMode": Image.Stretch },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Centered"), "fillMode": Image.Pad },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Tiled"), "fillMode": Image.Tile }
        ]
        onActivated: cfg_FillMode = currentValue
        Component.onCompleted: {
            for (var i = 0; i < model.length; i++) {
                if (model[i].fillMode === cfg_FillMode) {
                    currentIndex = i;
                    break;
                }
            }
        }
    }

    KQC2.ColorButton {
        id: colorButton
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Background color:")
        dialogTitle: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Select Background Color")
    }

    QQC2.CheckBox {
        text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Show desktop notifications")
        checked: cfg_NotifyEvents
        onToggled: cfg_NotifyEvents = checked
    }
}
