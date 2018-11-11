'use strict';
 
var gulp = require('gulp');
var sass = require('gulp-sass');
 
sass.compiler = require('node-sass');

const sassDirectory = './pjuu/static/scss/**/*.scss'

gulp.task('sass', () => {
    return gulp.src(sassDirectory)
        .pipe(sass().on('error', sass.logError))
        .pipe(gulp.dest('./pjuu/static/css'));
});
 
gulp.task('sass:watch', () => {
    gulp.watch(sassDirectory, ['sass']);
});

gulp.task('default', ['sass']);
