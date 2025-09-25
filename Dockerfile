FROM baseImage
COPY . /app
WORKDIR /app
RUN make /app
CMD python app.py