FROM prairielearn/grader-r

# Install R packages
RUN Rscript -e "install.packages('openintro')"

# Copy in Python grading script
COPY entrypoint.py /r_autograder/entrypoint.py

LABEL org.opencontainers.image.source=https://github.com/Bluesy1/OPB-docker-images
