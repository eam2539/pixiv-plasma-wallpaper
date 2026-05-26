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
    property int cfg_RotateMinutes
    property int cfg_FetchCount
    property string cfg_LocalImagePaths
    property string cfg_RotationMode
    property bool cfg_IncludeLocalImages
    property int cfg_LocalImageRatio
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

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Fetch every:")
        from: 5
        to: 10080
        value: cfg_RefreshMinutes
        textFromValue: function(value) { return i18ndp("plasma_wallpaper_org.pixiv.wallpaper", "%1 minute", "%1 minutes", value); }
        valueFromText: function(text) { return parseInt(text) || value; }
        onValueModified: cfg_RefreshMinutes = value
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Rotate every:")
        from: 1
        to: 1440
        value: cfg_RotateMinutes
        textFromValue: function(value) { return i18ndp("plasma_wallpaper_org.pixiv.wallpaper", "%1 minute", "%1 minutes", value); }
        valueFromText: function(text) { return parseInt(text) || value; }
        onValueModified: cfg_RotateMinutes = value
    }

    QQC2.SpinBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Fetch count:")
        from: 1
        to: 50
        value: cfg_FetchCount
        onValueModified: cfg_FetchCount = value
    }

    QQC2.TextArea {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Local image paths:")
        Layout.fillWidth: true
        implicitHeight: Kirigami.Units.gridUnit * 5
        text: cfg_LocalImagePaths
        placeholderText: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "One file or folder per line")
        wrapMode: TextEdit.WrapAnywhere
        onTextChanged: cfg_LocalImagePaths = text
    }

    QQC2.ComboBox {
        id: rotationModeCombo
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Rotation mode:")
        textRole: "label"
        valueRole: "value"
        model: [
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Sequential"), "value": "sequential" },
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Random"), "value": "random" }
        ]
        onActivated: cfg_RotationMode = currentValue
        Component.onCompleted: {
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

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Local image ratio:")
        Layout.fillWidth: true
        enabled: cfg_IncludeLocalImages

        QQC2.Slider {
            Layout.fillWidth: true
            from: 0
            to: 100
            stepSize: 5
            value: cfg_LocalImageRatio
            onMoved: cfg_LocalImageRatio = Math.round(value)
        }

        QQC2.Label {
            text: i18nd("plasma_wallpaper_org.pixiv.wallpaper", "%1% local", cfg_LocalImageRatio)
        }
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
            { "label": i18nd("plasma_wallpaper_org.pixiv.wallpaper", "Centered"), "fillMode": Image.Pad }
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
