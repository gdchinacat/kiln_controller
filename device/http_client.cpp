#include <Arduino.h>
#include "esp_http_client.h"
#include "esp_tls.h"

boo

class MyHTTPClient {
private:
    const char* _request_header_buf;
    size_t _header_len;
    esp_tls_cfg_t _tls_config;
    esp_tls_t* _tls_handle;

public:
    // 1. Constructor: Generates the entire immutable header string once during setup()
    MyHTTPClient(esp_http_client_config_t* base_config, const char* custom_headers = NULL) {
        _request_header_buf = NULL;
        _header_len = 0;
        _tls_handle = NULL;

        // Initialize persistent configuration tracking profile
        memset(&_tls_config, 0, sizeof(esp_tls_cfg_t));
        _tls_config.timeout_ms = base_config->timeout_ms > 0 ? base_config->timeout_ms : 1500;
        _tls_config.non_block = false;

        // Instantiate a brief, temporary client to cleanly format the standard HTTP text blocks
        esp_http_client_handle_t temp_client = esp_http_client_init(base_config);
        if (temp_client != NULL) {
            // Apply custom parameters if passed by the setup block
            if (custom_headers != NULL) {
                // Parse and append hooks if necessary via standard set_header wrappers
                esp_http_client_set_header(temp_client, "Content-Type", "application/octet-stream");
            }

            // Extract internal parameters to assemble the target raw header block.
            // Note: Since esp_http_client hides internal string generation until open() is called, 
            // we mirror standard RFC 2616 header formatting directly using the safe setup configuration parameters:
            size_t path_len = strlen(base_config->path ? base_config->path : "/");
            size_t host_len = strlen(base_config->host);
            
            // Calculate buffer bounds for a single contiguous string allocation
            size_t allocation_size = path_len + host_len + 128; // Add safe margin padding for static tokens
            if (custom_headers) allocation_size += strlen(custom_headers);

            _request_header_buf = (char*)malloc(allocation_size);
            if (_request_header_buf != NULL) {
                _header_len = snprintf(_request_header_buf, allocation_size,
                    "POST %s HTTP/1.1\r\n"
                    "Host: %s\r\n"
                    "Content-Type: application/octet-stream\r\n"
                    "%s"
                    "\r\n",
                    base_config->path ? base_config->path : "/",
                    base_config->host,
                    custom_headers ? custom_headers : "");
            }

            // Completely destroy the configuration engine instance. 
            // The generated text block is now permanently locked into _request_header_buf.
            esp_http_client_cleanup(temp_client);
        }
    }

    // Destructor to clean up the initial setup allocation
    ~MyHTTPClient() {
        if (_request_header_buf != NULL) {
            free(_request_header_buf);
        }
        disconnect();
    }

    // Explicit network connection state step
    bool connect(const char* host, int port) {
        disconnect(); // Clear any zombie or stalled sockets from previous intervals cleanly
        
        // Establishes connection and runs the full TLS math handshake using our persistent config profile
        _tls_handle = esp_tls_conn_new_sync(host, port, &_tls_config);
        return (_tls_handle != NULL);
    }

    void disconnect() {
        if (_tls_handle != NULL) {
            // Destroys internal mbedTLS tracking frames and closes raw BSD file descriptors safely
            esp_tls_conn_destroy(_tls_handle);
            _tls_handle = NULL;
        }
    }

    // 2. Send: Transmits the immutable header buffer directly followed by the ring buffer data pointer
    bool send_headers(size_t content_length) {
        if (_tls_handle == NULL) return false;

        // Write immutable pre-compiled header text frame
        int written = esp_tls_conn_write(_tls_handle, _request_header_buf, _header_len);
        if (written < 0) return false;

        // If your server expects a dynamic Content-Length header, we inject it line-by-line here:
        char length_buf[32];
        int len_str_bytes = snprintf(length_buf, sizeof(length_buf), "Content-Length: %d\r\n\r\n", content_length);
        written = esp_tls_conn_write(_tls_handle, length_buf, len_str_bytes);
        
        return (written >= 0);
    }

    bool send_body_chunk(const uint8_t* data, size_t len) {
        if (_tls_handle == NULL || data == NULL || len == 0) return false;
        int written = esp_tls_conn_write(_tls_handle, data, len);
        return (written >= 0);
    }

    // Parses raw status responses to verify transaction tracking properties
    int read_http_status() {
        if (_tls_handle == NULL) return -1;

        char peek_buf[32];
        // Read initial raw bytes cleanly off the top of the incoming socket buffer without draining it
        int read_bytes = esp_tls_conn_read(_tls_handle, peek_buf, sizeof(peek_buf) - 1);
        if (read_bytes <= 0) return -1;
        peek_buf[read_bytes] = '\0';

        if (strncmp(peek_buf, "HTTP/1.", 7) == 0) {
            return atoi(peek_buf + 9); // Extract integer representation from "HTTP/1.1 200 OK"
        }
        return -1;
    }

    // 3. Response Processing: Exposes direct chunk reading capability to the loop execution framework
    int read_response_body(char* target_buffer, size_t max_buffer_len) {
        if (_tls_handle == NULL || target_buffer == NULL || max_buffer_len == 0) {
            return -1;
        }
        // Direct non-allocating data pipeline read straight into user-provided static target arrays
        return esp_tls_conn_read(_tls_handle, target_buffer, max_buffer_len);
    }
};

