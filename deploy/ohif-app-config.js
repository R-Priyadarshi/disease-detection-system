/**
 * OHIF Diagnostic Viewer v3 - ALVEON Enterprise DICOMweb Data Source Configuration
 * Conforms to Open Health Imaging Foundation (OHIF) Viewer v3.x and Cornerstone3D.
 * 100% Free, Open-Source (MIT), zero licensing cost.
 */

window.config = {
  routerBasename: '/',
  showStudyList: true,
  extensions: [],
  modes: [],
  customizationService: {},
  showWarningMessageForCrossOrigin: false,
  showCPUFallbackMessage: false,
  showLoadingIndicator: true,
  strictZSpacingForVolumeViewport: true,
  dataSources: [
    {
      friendlyName: 'ALVEON Enterprise Thoracic PACS & DICOMweb Archive',
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        name: 'ALVEON_PACS',
        wadoUriRoot: '/dicomweb',
        qidoRoot: '/dicomweb',
        wadoRoot: '/dicomweb',
        qidoSupportsIncludeField: false,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: true,
        supportsWildcard: true,
        staticWado: false,
        singlepart: 'bulkdata,video,pdf',
        acceptHeader: [
          'multipart/related; type=image/jpeg',
          'multipart/related; type=application/octet-stream'
        ]
      }
    }
  ],
  defaultDataSourceName: 'dicomweb',
  hotkeys: [
    { commandName: 'incrementActiveViewport', label: 'Next Viewport', keys: ['right'] },
    { commandName: 'decrementActiveViewport', label: 'Previous Viewport', keys: ['left'] },
    { commandName: 'rotateViewportCW', label: 'Rotate Right', keys: ['r'] },
    { commandName: 'rotateViewportCCW', label: 'Rotate Left', keys: ['l'] },
    { commandName: 'invertViewport', label: 'Invert Color', keys: ['i'] },
    { commandName: 'flipViewportHorizontal', label: 'Flip H', keys: ['h'] },
    { commandName: 'flipViewportVertical', label: 'Flip V', keys: ['v'] },
    { commandName: 'scaleUpViewport', label: 'Zoom In', keys: ['+'] },
    { commandName: 'scaleDownViewport', label: 'Zoom Out', keys: ['-'] },
    { commandName: 'fitViewportToWindow', label: 'Zoom to Fit', keys: ['space'] },
    { commandName: 'resetViewport', label: 'Reset Viewport', keys: ['space'] }
  ]
};
