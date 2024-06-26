FROM prairielearn/grader-r

# Install R packages
RUN Rscript -e "install.packages('openintro')"

# Copy in Python grading script
COPY entrypoint.py /r_autograder/entrypoint.py

