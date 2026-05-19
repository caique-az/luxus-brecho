const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

config.transformer.minifierPath = 'metro-minify-terser';
config.resolver.sourceExts.push('cjs');

module.exports = config;